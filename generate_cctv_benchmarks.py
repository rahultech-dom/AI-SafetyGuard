"""Generate dedicated CCTV scenario footages with realistic surveillance visual artifacts:
fixed camera perspective, CCTV HUD timestamp watermark, camera noise, and clear ground-truth actions."""

import cv2
import numpy as np
from pathlib import Path

DATA_VIDEOS_DIR = Path("data/videos")
DATA_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

def add_cctv_hud(frame, camera_name, frame_idx, fps):
    h, w = frame.shape[:2]
    # Dark translucent bar on top
    cv2.rectangle(frame, (0, 0), (w, 32), (20, 20, 20), -1)
    sec = frame_idx / fps
    mins = int(sec // 60)
    secs = int(sec % 60)
    ms = int((sec % 1) * 100)
    time_str = f"2026-10-17 18:{mins:02d}:{secs:02d}.{ms:02d} - REC"
    cv2.putText(frame, camera_name, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
    cv2.putText(frame, time_str, (w - 240, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 220, 220), 1)
    
    # Slight CCTV scanline / grain
    noise = np.random.normal(0, 2, (h, w, 3)).astype(np.int16)
    frame_noise = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return frame_noise

def generate_cctv_normal_store():
    out_path = DATA_VIDEOS_DIR / "cctv_normal_store_counter.mp4"
    fps = 20
    duration = 8.0
    total_frames = int(fps * duration)
    w, h = 640, 360
    
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for i in range(total_frames):
        frame = np.full((h, w, 3), (210, 215, 220), dtype=np.uint8)
        # Store counter
        cv2.rectangle(frame, (100, 220), (540, 320), (140, 120, 100), -1)
        cv2.putText(frame, "CHECKOUT COUNTER", (220, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Cashier standing still behind counter
        cv2.circle(frame, (250, 180), 18, (80, 80, 160), -1)
        cv2.line(frame, (250, 198), (250, 240), (80, 80, 160), 6)
        
        # Customer walking in smoothly from right to counter, pauses, then walks
        t = i / total_frames
        if t < 0.4:
            cust_x = int(600 - (t / 0.4) * 220)
        elif t < 0.7:
            cust_x = 380  # standing at counter
        else:
            cust_x = int(380 + ((t - 0.7) / 0.3) * 220)
            
        bob = int(2 * abs(np.sin(i * 0.4)))
        cv2.circle(frame, (cust_x, 180 - bob), 18, (160, 90, 60), -1)
        cv2.line(frame, (cust_x, 198 - bob), (cust_x, 260), (160, 90, 60), 6)
        
        frame = add_cctv_hud(frame, "CAM-01 [STORE_FRONT]", i, fps)
        writer.write(frame)
    writer.release()
    print(f"Generated: {out_path.name}")

def generate_cctv_normal_hallway():
    out_path = DATA_VIDEOS_DIR / "cctv_normal_hallway_patrol.mp4"
    fps = 20
    duration = 8.0
    total_frames = int(fps * duration)
    w, h = 640, 360
    
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for i in range(total_frames):
        frame = np.full((h, w, 3), (225, 225, 225), dtype=np.uint8)
        # Corridor perspective lines
        cv2.line(frame, (0, 0), (240, 140), (180, 180, 180), 2)
        cv2.line(frame, (640, 0), (400, 140), (180, 180, 180), 2)
        cv2.line(frame, (0, 360), (240, 240), (180, 180, 180), 2)
        cv2.line(frame, (640, 360), (400, 240), (180, 180, 180), 2)
        
        # Person 1 walking forward towards camera
        t = i / total_frames
        p1_y = int(170 + t * 90)
        p1_x = int(320 - t * 40)
        scale = 0.7 + t * 0.6
        radius = int(14 * scale)
        bob = int(2 * abs(np.sin(i * 0.35)))
        cv2.circle(frame, (p1_x, p1_y - bob), radius, (50, 120, 180), -1)
        cv2.line(frame, (p1_x, p1_y - bob + radius), (p1_x, p1_y + int(40 * scale)), (50, 120, 180), int(4 * scale))
        
        frame = add_cctv_hud(frame, "CAM-04 [CORRIDOR_WEST]", i, fps)
        writer.write(frame)
    writer.release()
    print(f"Generated: {out_path.name}")

def generate_cctv_crime_brawl():
    out_path = DATA_VIDEOS_DIR / "cctv_crime_altercation_brawl.mp4"
    fps = 20
    duration = 10.0
    total_frames = int(fps * duration)
    w, h = 640, 360
    
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for i in range(total_frames):
        frame = np.full((h, w, 3), (215, 220, 220), dtype=np.uint8)
        cv2.line(frame, (0, 280), (w, 280), (100, 100, 100), 2)
        
        t = i / fps
        # Phase 1 (0s - 3s): Normal approach
        if t < 3.0:
            x1 = int(220 + (t / 3.0) * 40)
            x2 = int(420 - (t / 3.0) * 80)
            cv2.circle(frame, (x1, 160), 18, (60, 80, 180), -1)
            cv2.line(frame, (x1, 178), (x1, 240), (60, 80, 180), 6)
            cv2.circle(frame, (x2, 160), 18, (180, 60, 60), -1)
            cv2.line(frame, (x2, 178), (x2, 240), (180, 60, 60), 6)
        # Phase 2 (3s - 7.5s): Violent struggle / physical grappling
        elif t < 7.5:
            # Chaotic rapid displacement (high jerk)
            shake_x1 = int(np.random.uniform(-25, 25))
            shake_y1 = int(np.random.uniform(-18, 18))
            shake_x2 = int(np.random.uniform(-25, 25))
            shake_y2 = int(np.random.uniform(-18, 18))
            
            x1 = 290 + shake_x1
            y1 = 170 + shake_y1
            x2 = 320 + shake_x2
            y2 = 175 + shake_y2
            
            # Entangled figures struggling
            cv2.circle(frame, (x1, y1), 18, (60, 80, 180), -1)
            cv2.line(frame, (x1, y1 + 18), (x1, y1 + 75), (60, 80, 180), 7)
            cv2.line(frame, (x1, y1 + 30), (x2, y2 + 25), (60, 80, 180), 5)  # grappling arm
            
            cv2.circle(frame, (x2, y2), 18, (180, 60, 60), -1)
            cv2.line(frame, (x2, y2 + 18), (x2, y2 + 75), (180, 60, 60), 7)
            cv2.line(frame, (x2, y2 + 35), (x1, y1 + 30), (180, 60, 60), 5)  # tackling arm
        # Phase 3 (7.5s - 10s): One pinned down, one standing over
        else:
            # Person 1 knocked to ground
            cv2.ellipse(frame, (280, 260), (35, 14), 0, 0, 360, (60, 80, 180), -1)
            cv2.circle(frame, (240, 255), 15, (60, 80, 180), -1)
            # Person 2 standing over
            cv2.circle(frame, (350, 160), 18, (180, 60, 60), -1)
            cv2.line(frame, (350, 178), (350, 250), (180, 60, 60), 6)
            
        frame = add_cctv_hud(frame, "CAM-02 [PARKING_LOT]", i, fps)
        writer.write(frame)
    writer.release()
    print(f"Generated: {out_path.name}")

def generate_cctv_crime_fall():
    out_path = DATA_VIDEOS_DIR / "cctv_crime_slip_fall.mp4"
    fps = 20
    duration = 8.0
    total_frames = int(fps * duration)
    w, h = 640, 360
    
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for i in range(total_frames):
        frame = np.full((h, w, 3), (230, 228, 225), dtype=np.uint8)
        cv2.line(frame, (0, 280), (w, 280), (120, 120, 120), 2)
        
        t = i / fps
        if t < 3.0:
            # Walking normally
            x = int(120 + (t / 3.0) * 160)
            bob = int(2 * abs(np.sin(i * 0.4)))
            cv2.circle(frame, (x, 150 - bob), 18, (40, 140, 100), -1)
            cv2.line(frame, (x, 168 - bob), (x, 240), (40, 140, 100), 6)
        elif t < 4.2:
            # Sudden slip and violent collapse
            slip_frac = (t - 3.0) / 1.2
            x = int(280 + slip_frac * 40)
            y = int(150 + slip_frac * 115)
            angle = int(slip_frac * 85)
            # Tilted body falling rapidly
            cv2.circle(frame, (x - int(angle * 0.5), y), 18, (40, 140, 100), -1)
            cv2.line(frame, (x - int(angle * 0.5), y), (x + 30, y + 15), (40, 140, 100), 7)
        else:
            # Lying motionless on floor (requiring assistance)
            cv2.circle(frame, (270, 265), 16, (40, 140, 100), -1)
            cv2.line(frame, (270, 265), (340, 270), (40, 140, 100), 8)
            
        frame = add_cctv_hud(frame, "CAM-05 [STAIRWELL_EXIT]", i, fps)
        writer.write(frame)
    writer.release()
    print(f"Generated: {out_path.name}")

if __name__ == "__main__":
    generate_cctv_normal_store()
    generate_cctv_normal_hallway()
    generate_cctv_crime_brawl()
    generate_cctv_crime_fall()
