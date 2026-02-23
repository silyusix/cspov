import os
import time
import json
import socket
import threading
import glob
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

try:
    from demoparser2 import DemoParser
except ImportError:
    print(" 错误：缺少 demoparser2")
    exit()

GAME_DIR = r"D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo"
VIDEO_DIR = r"D:\hlae\videos"
TELNET_PORT = 2121
GSI_PORT = 3333 

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

class MasterManager:
    def __init__(self):
        self.target_name = ""
        self.total_rounds = 0
        self.current_round = 1 
        self.round_ticks = [] 
        self.is_active = False
        self.is_processing = False 
        self.has_started = False
        self.conn = self.CS2Connection(TELNET_PORT)
        self.last_ct_score = -1
        self.last_t_score = -1
        
    class CS2Connection:
        def __init__(self, port):
            self.port = port
            self.sock = None
        def connect(self):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(2)
                self.sock.connect(("127.0.0.1", self.port))
                return True
            except: return False
        def send(self, cmd):
            if self.sock:
                try: self.sock.send(f"{cmd}\n".encode('utf-8'))
                except: pass

    def find_and_parse_demo(self):
        dem_files = glob.glob(os.path.join(GAME_DIR, "*.dem"))
        if not dem_files: return None, False
        latest_dem = max(dem_files, key=os.path.getctime)
        try:
            parser = DemoParser(latest_dem)
            players = parser.parse_ticks(["name"]).dropna().drop_duplicates(subset=['name'])
            player_list = [{"name": row['name']} for _, row in players.iterrows() if row['name'] not in ["GOTV", "BOT"]]
            
            events = parser.parse_event("round_freeze_end")
            all_ticks = sorted([t for t in events['tick'].tolist() if t > 1000])
            
            print(f" 解析完毕。Demo内共 {len(all_ticks)} 个回合。")
            user_input = input(f"请输入正赛局数 (faceit存在拼刀，会多解析两个): ")
            match_rounds = int(user_input) if user_input.isdigit() else len(all_ticks)
            self.round_ticks = all_ticks[-match_rounds:]
            self.total_rounds = len(self.round_ticks)
            return player_list, True
        except: return None, False

    def setup_pov_cfg(self):
        first_tick = max(0, self.round_ticks[0] - 320)
        pov_path = os.path.join(GAME_DIR, "cfg", "pov.cfg")
        with open(pov_path, "w", encoding="utf-8") as f:
            f.write('mirv_streams removeAll\n')
            f.write('mirv_streams add normal pov\n')
            f.write('mirv_streams edit pov captureType rgb\n') 
            f.write('mirv_streams settings remove my_v\n')
            ffmpeg_cmd = '-c:v hevc_nvenc -preset p4 -rc vbr -cq 28 -vf scale=3840:2160 -pix_fmt yuv420p'
            f.write(f'mirv_streams settings add ffmpeg my_v "{ffmpeg_cmd} -y {{QUOTE}}{VIDEO_DIR}/pov.mp4{{QUOTE}}"\n')
            f.write('mirv_streams edit pov settings my_v\n')
            f.write('host_framerate 60\n')
            f.write('spec_autodirector 0\n')
            f.write(f'bind F5 "demo_gototick {first_tick}; demo_pause; echo [READY]"\n')
            f.write('bind F6 "mirv_streams record end; demo_pause"\n')

    def execute_combo(self, is_first_round=False):
        if self.is_processing: return
        self.is_processing = True
        
        if not is_first_round:
            time.sleep(1.0)
            self.conn.send("mirv_streams record end; demo_pause")
            if self.current_round >= self.total_rounds:
                print("全部完成！")
                self.is_active = False
                return
            
            target_tick = max(0, self.round_ticks[self.current_round] - 320)
            self.current_round += 1
            print(f"\n跳转至下一局...")
            self.conn.send("host_framerate 0") 
            self.conn.send(f"demo_gototick {target_tick}")
            time.sleep(1.0) 
            self.conn.send("host_framerate 60")
            self.conn.send("demo_timescale 1; demo_resume")
        else:
            print(f"\n 第一局启动中...")
            time.sleep(1.5)
            self.conn.send(f'spec_player "{self.target_name}"')
            time.sleep(0.5)
            self.conn.send("demo_timescale 1; demo_resume")

        time.sleep(1.5) 
        self.conn.send(f'spec_player "{self.target_name}"')
        time.sleep(1.0) 
        print(f"开启录制 ({self.current_round}/{self.total_rounds})")
        self.conn.send("mirv_streams record start")
        
        time.sleep(5)
        self.is_processing = False

    def monitor_files(self):
        target = os.path.join(VIDEO_DIR, "pov.mp4")
        while True:
            if os.path.exists(target):
                try:
                    time.sleep(1.0)
                    files = os.listdir(VIDEO_DIR)
                    existing_nums = [int(f[:-4]) for f in files if f.endswith(".mp4") and f[:-4].isdigit()]
                    next_idx = max(existing_nums + [0]) + 1
                    os.rename(target, os.path.join(VIDEO_DIR, f"{next_idx}.mp4"))
                    print(f"归档成功: {next_idx}.mp4")
                except: pass
            time.sleep(1)

def run_gsi_server(manager):
    class GSIHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                length = int(self.headers['Content-Length'])
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                health = data.get('player', {}).get('state', {}).get('health', 100)
                phase = data.get('round', {}).get('phase', '')
                if manager.is_active and not manager.is_processing:
                    if not manager.has_started and phase == "freezetime":
                        manager.has_started = True
                        threading.Thread(target=manager.execute_combo, args=(True,)).start()
                    elif manager.has_started and (health == 0 or phase == "over"):
                        threading.Thread(target=manager.execute_combo, args=(False,)).start()
                self.send_response(200); self.end_headers()
            except: pass
        def log_message(self, format, *args): return
    try:
        server = ThreadedHTTPServer(('127.0.0.1', GSI_PORT), GSIHandler)
        server.serve_forever()
    except: pass

if __name__ == "__main__":
    print("HLAE pov")
    manager = MasterManager()
    player_list, success = manager.find_and_parse_demo()
    if success:
        for i, p in enumerate(player_list): print(f"[{i+1}] {p['name']}")
        try:
            idx = int(input("\n确认录制人: ")) - 1
            manager.target_name = player_list[idx]['name']
            manager.setup_pov_cfg()
        except: exit()
    while not manager.conn.connect(): time.sleep(2)
    print("\n已就绪！请进游戏 exec pov 后按 F5 一键开始全自动流程。")
    manager.is_active = True
    threading.Thread(target=run_gsi_server, args=(manager,), daemon=True).start()
    manager.monitor_files()
