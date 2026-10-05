"""
Space Shooter v2 - an improved demo in pure Python (tkinter only)

Run: space_shooter_v2.py

Controls:
  Move:    Arrow keys or W A S D
  Shoot:   Space (hold , toggle )
  Pause:   P or Esc
  Restart: R or Enter (while paused / on Game Over)

"""

import math
import os
import random
import sys
import time
import tkinter as tk

W, H = 480, 640
DT = 1 / 60         
MAX_LIVES = 5

WIN_KEYS = {37: "left", 38: "up", 39: "right", 40: "down", 32: "space",
            87: "w", 65: "a", 83: "s", 68: "d", 80: "p", 82: "r",
            13: "return", 27: "escape"}
LINUX_KEYS = {25: "w", 38: "a", 39: "s", 40: "d", 33: "p", 27: "r"}

ENEMY = {
    "basic":  dict(hp=1, size=(14, 22), speed=(2.0, 3.2), pts=10, color="#ff4466"),
    "fast":   dict(hp=1, size=(10, 13), speed=(5.0, 6.5), pts=20, color="#ffcc33"),
    "zigzag": dict(hp=2, size=(14, 18), speed=(2.0, 2.8), pts=25, color="#44ff99"),
    "tank":   dict(hp=4, size=(26, 30), speed=(1.0, 1.6), pts=40, color="#aa66ff"),
}
POWER = {"triple": ("T", "#33ddff"), "shield": ("S", "#5588ff"), "life": ("+", "#ff6699")}


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Space Shooter v2")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=W, height=H, bg="#0b0b1e", highlightthickness=0)
        self.canvas.pack()
        root.focus_force()

        self.keys = set()
        self.release_jobs = {}
        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)

        self.score_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")
        self.highscore = self.load_highscore()

        self.stars = [[random.randint(0, W), random.randint(0, H), random.choice([1, 2, 3])]
                      for _ in range(70)]
        self.frame = 0
        self.reset()
        self.state = "menu"

        self.last = time.perf_counter()
        self.acc = 0.0
        self.loop()

    def load_highscore(self):
        try:
            with open(self.score_file) as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def save_highscore(self):
        try:
            with open(self.score_file, "w") as f:
                f.write(str(self.highscore))
        except Exception:
            pass

    # ---------- game state ----------
    def reset(self):
        self.state = "play"
        self.paused = False
        self.px, self.py = W / 2, H - 70
        self.lives = 3
        self.shield = False
        self.triple = 0
        self.invincible = 0
        self.cooldown = 0
        self.flash = 0
        self.score = 0
        self.level = 1
        self.banner = 90
        self.combo = 0
        self.combo_timer = 0
        self.spawn_timer = 30
        self.over_timer = 0
        self.bullets, self.enemies, self.particles = [], [], []
        self.powerups, self.popups = [], []

    def norm(self, e):
        if sys.platform == "win32" and e.keycode in WIN_KEYS:
            return WIN_KEYS[e.keycode]
        if sys.platform.startswith("linux") and e.keycode in LINUX_KEYS:
            return LINUX_KEYS[e.keycode]
        return e.keysym.lower()

    def on_key_down(self, e):
        k = self.norm(e)
        job = self.release_jobs.pop(k, None)
        if job:                       
            self.root.after_cancel(job)
        if k not in self.keys:        
            self.keys.add(k)
            self.just_pressed(k)

    def on_key_up(self, e):
        k = self.norm(e)
        self.release_jobs[k] = self.root.after(25, lambda: self.release(k))

    def release(self, k):
        self.keys.discard(k)
        self.release_jobs.pop(k, None)

    def pressed(self, *names):
        return any(n in self.keys for n in names)

    def just_pressed(self, k):
        if self.state == "menu" and k in ("space", "return"):
            self.reset()
        elif self.state == "play" and k in ("p", "escape"):
            self.paused = not self.paused
        elif k in ("r", "return") and (self.paused or self.state == "over"):
            self.reset()

    # ---------- logic ----------
    def explode(self, x, y, n, color="#ffaa33"):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(1, 4)
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s,
                                   random.randint(15, 30), color])

    def spawn_enemy(self):
        lv = self.level
        weights = {"basic": 10,
                   "fast": 0 if lv < 2 else 3 + lv,
                   "zigzag": 0 if lv < 3 else 2 + lv,
                   "tank": 0 if lv < 4 else 1 + lv // 2}
        kind = random.choices(list(weights), list(weights.values()))[0]
        d = ENEMY[kind]
        size = random.randint(*d["size"])
        x = random.randint(size + 60, W - size - 60)
        self.enemies.append(dict(t=kind, x=x, x0=x, y=-size, size=size, hp=d["hp"],
                                 maxhp=d["hp"], vy=random.uniform(*d["speed"]) + lv * 0.1,
                                 phase=random.uniform(0, 6.28), hit=0))

    def kill_enemy(self, en):
        self.enemies.remove(en)
        d = ENEMY[en["t"]]
        self.explode(en["x"], en["y"], 8 + en["size"] // 2, d["color"])
        self.combo += 1
        self.combo_timer = 150
        pts = d["pts"] * min(5, 1 + self.combo // 5)
        self.score += pts
        self.popups.append([en["x"], en["y"], f"+{pts}", 40])
        if random.random() < (0.35 if en["t"] == "tank" else 0.10):
            kind = random.choice(["triple", "triple", "shield", "life"])
            self.powerups.append(dict(kind=kind, x=en["x"], y=en["y"]))

    def hurt_player(self):
        if self.invincible > 0:
            return
        if self.shield:
            self.shield = False
            self.invincible = 45
            self.explode(self.px, self.py, 10, "#5588ff")
            return
        self.lives -= 1
        self.invincible = 100
        self.flash = 15
        self.combo = 0
        self.explode(self.px, self.py, 25)
        if self.lives <= 0:
            self.state = "over"
            if self.score > self.highscore:
                self.highscore = self.score
                self.save_highscore()

    def update(self):
        self.frame += 1
        for s in self.stars:
            s[1] += s[2]
            if s[1] > H:
                s[0], s[1] = random.randint(0, W), 0

        if self.state == "over":
            self.over_timer += 1
        if self.state != "play" or self.paused:
            return

        # movement (diagonal speed is normalized)
        dx = (self.pressed("right", "d")) - (self.pressed("left", "a"))
        dy = (self.pressed("down", "s")) - (self.pressed("up", "w"))
        if dx and dy:
            dx *= 0.707
            dy *= 0.707
        self.px = max(20, min(W - 20, self.px + dx * 5.5))
        self.py = max(40, min(H - 30, self.py + dy * 5.5))

        # shooting
        self.cooldown = max(0, self.cooldown - 1)
        if self.pressed("space") and self.cooldown == 0:
            vxs = (-2.5, 0, 2.5) if self.triple > 0 else (0,)
            for vx in vxs:
                self.bullets.append([self.px, self.py - 22, vx])
            self.cooldown = 9
        self.triple = max(0, self.triple - 1)
        self.invincible = max(0, self.invincible - 1)
        self.flash = max(0, self.flash - 1)
        self.banner = max(0, self.banner - 1)

        for b in self.bullets:
            b[0] += b[2]
            b[1] -= 11
        self.bullets = [b for b in self.bullets if b[1] > -10 and -10 < b[0] < W + 10]

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_enemy()
            self.spawn_timer = max(14, int(50 - self.level * 4) + random.randint(-6, 6))

        for en in self.enemies:
            en["y"] += en["vy"]
            en["hit"] = max(0, en["hit"] - 1)
            if en["t"] == "zigzag":
                en["phase"] += 0.07
                en["x"] = max(en["size"], min(W - en["size"], en["x0"] + math.sin(en["phase"]) * 70))
        self.enemies = [e for e in self.enemies if e["y"] < H + 40]

        # bullet <-> enemy collisions
        for b in self.bullets[:]:
            for en in self.enemies:
                if abs(b[0] - en["x"]) < en["size"] and abs(b[1] - en["y"]) < en["size"]:
                    self.bullets.remove(b)
                    en["hp"] -= 1
                    en["hit"] = 4
                    if en["hp"] <= 0:
                        self.kill_enemy(en)
                    break

        # enemy <-> player collisions
        for en in self.enemies[:]:
            if abs(self.px - en["x"]) < en["size"] + 10 and abs(self.py - en["y"]) < en["size"] + 10:
                if self.invincible == 0:
                    self.enemies.remove(en)
                    self.explode(en["x"], en["y"], 10, ENEMY[en["t"]]["color"])
                    self.hurt_player()
                    break

        for p in self.powerups[:]:
            p["y"] += 2
            if math.hypot(p["x"] - self.px, p["y"] - self.py) < 26:
                self.powerups.remove(p)
                if p["kind"] == "triple":
                    self.triple = 600
                elif p["kind"] == "shield":
                    self.shield = True
                else:
                    self.lives = min(MAX_LIVES, self.lives + 1)
                self.popups.append([self.px, self.py - 30, p["kind"].upper(), 40])
            elif p["y"] > H + 20:
                self.powerups.remove(p)

        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0
        new_level = 1 + self.score // 400
        if new_level > self.level:
            self.level = new_level
            self.banner = 120

        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for t in self.popups:
            t[1] -= 0.8
            t[3] -= 1
        self.popups = [t for t in self.popups if t[3] > 0]

    def draw_enemy(self, en):
        c, x, y, s = self.canvas, en["x"], en["y"], en["size"]
        col = "#ffffff" if en["hit"] else ENEMY[en["t"]]["color"]
        if en["t"] == "basic":
            pts = [x - s, y - s, x + s, y - s, x, y + s]
        elif en["t"] == "fast":
            pts = [x, y - s * 1.6, x + s, y, x, y + s * 1.6, x - s, y]
        elif en["t"] == "zigzag":
            pts = [x - s, y, x - s / 2, y - s, x + s / 2, y - s, x + s, y, x, y + s]
        else:
            pts = [x - s, y - s / 2, x - s / 2, y - s, x + s / 2, y - s,
                   x + s, y - s / 2, x + s, y + s / 2, x, y + s, x - s, y + s / 2]
        c.create_polygon(pts, fill=col, outline="#ffffff", width=2)
        if en["maxhp"] > 1:
            w = s * 2 * en["hp"] / en["maxhp"]
            c.create_rectangle(x - s, y - s - 8, x - s + w, y - s - 5, fill="#66ff66", outline="")

    def text(self, x, y, s, size=14, color="white", anchor="center", bold=True):
        self.canvas.create_text(x, y, text=s, fill=color, anchor=anchor,
                                font=("Arial", size, "bold" if bold else "normal"))

    def draw(self):
        c = self.canvas
        c.delete("all")
        for x, y, spd in self.stars:
            col = {1: "#444466", 2: "#8888aa", 3: "#ffffff"}[spd]
            c.create_rectangle(x, y, x + spd, y + spd, fill=col, outline="")

        if self.state == "menu":
            self.text(W / 2, 200, "SPACE SHOOTER", 32, "#44ddff")
            self.text(W / 2, 250, "Python Demo v2", 14, "#8888aa", bold=False)
            self.text(W / 2, 340, "Arrows / WASD : Move", 13, bold=False)
            self.text(W / 2, 368, "Space : Shoot (hold)", 13, bold=False)
            self.text(W / 2, 396, "P / Esc : Pause", 13, bold=False)
            if self.frame % 60 < 40:
                self.text(W / 2, 480, "Press SPACE to start", 18, "#ffcc33")
            self.text(W / 2, 540, f"High score: {self.highscore}", 14, "#aaaaaa")
            return

        for p in self.particles:
            r = p[4] / 10
            c.create_oval(p[0] - r, p[1] - r, p[0] + r, p[1] + r, fill=p[5], outline="")
        for x, y, _ in self.bullets:
            c.create_rectangle(x - 2, y - 8, x + 2, y + 8, fill="#66ffff", outline="")
        for en in self.enemies:
            self.draw_enemy(en)
        for p in self.powerups:
            letter, col = POWER[p["kind"]]
            c.create_oval(p["x"] - 13, p["y"] - 13, p["x"] + 13, p["y"] + 13,
                          fill="#101030", outline=col, width=3)
            self.text(p["x"], p["y"], letter, 12, col)

        if self.state == "play" and (self.invincible == 0 or self.frame % 6 < 3):
            x, y = self.px, self.py
            c.create_polygon(x, y - 22, x - 18, y + 16, x, y + 8, x + 18, y + 16,
                             fill="#44ddff", outline="#ffffff", width=2)
            if self.shield:
                c.create_oval(x - 28, y - 28, x + 28, y + 28, outline="#5588ff", width=3)

        for x, y, s, _ in self.popups:
            self.text(x, y, s, 11, "#ffee88")

        # HUD
        self.text(10, 10, f"Score: {self.score}", 14, anchor="nw")
        self.text(10, 32, f"Best: {max(self.highscore, self.score)}", 10, "#aaaaaa", "nw", False)
        self.text(W / 2, 14, f"Level {self.level}", 12, "#ffcc33", "n")
        for i in range(self.lives):
            c.create_oval(W - 22 - i * 20, 12, W - 8 - i * 20, 26, fill="#ff4466", outline="")
        if self.combo >= 5:
            self.text(W - 10, 34, f"Combo x{min(5, 1 + self.combo // 5)}", 12, "#ffaa33", "ne")
        if self.triple > 0:
            c.create_rectangle(10, H - 16, 10 + self.triple / 6, H - 10, fill="#33ddff", outline="")

        if self.banner > 0 and self.state == "play":
            self.text(W / 2, 150, f"LEVEL {self.level}", 28, "#ffcc33")
        if self.flash > 0:
            c.create_rectangle(2, 2, W - 2, H - 2, outline="#ff2244", width=8)
        if self.paused:
            self.text(W / 2, H / 2 - 10, "PAUSED", 30)
            self.text(W / 2, H / 2 + 30, "P: resume   R: restart", 13, bold=False)
        if self.state == "over":
            self.text(W / 2, H / 2 - 40, "GAME OVER", 34, "#ff4466")
            self.text(W / 2, H / 2 + 5, f"Score: {self.score}   Best: {self.highscore}", 16)
            if self.score >= self.highscore and self.score > 0:
                self.text(W / 2, H / 2 + 35, "NEW HIGH SCORE!", 14, "#ffcc33")
            self.text(W / 2, H / 2 + 75, "Press R or Enter to restart", 13, bold=False)

    def loop(self):
        now = time.perf_counter()
        self.acc = min(self.acc + (now - self.last), 0.25)
        self.last = now
        while self.acc >= DT:
            self.update()
            self.acc -= DT
        self.draw()
        self.root.after(8, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
