import random
import tkinter as tk

W, H = 480, 640
FPS_MS = 16  


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Space Shooter Demo")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=W, height=H, bg="#0b0b1e", highlightthickness=0)
        self.canvas.pack()

        self.keys = set()
        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)

        self.stars = [[random.randint(0, W), random.randint(0, H), random.choice([1, 2, 3])]
                      for _ in range(70)]

        self.reset()
        self.loop()

    def reset(self):
        self.px, self.py = W / 2, H - 70
        self.bullets = []     
        self.enemies = []     
        self.particles = []    
        self.score = 0
        self.lives = 3
        self.cooldown = 0
        self.spawn_timer = 0
        self.invincible = 0
        self.frame = 0
        self.game_over = False
        self.paused = False

    def on_key_down(self, e):
        k = e.keysym.lower()
        self.keys.add(k)
        if k == "p" and not self.game_over:
            self.paused = not self.paused
        if k == "r":
            self.reset()

    def on_key_up(self, e):
        self.keys.discard(e.keysym.lower())

    def pressed(self, *names):
        return any(n in self.keys for n in names)

    def explode(self, x, y, n=12):
        for _ in range(n):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-3, 3)
            self.particles.append([x, y, vx, vy, random.randint(15, 30)])

    def update(self):
        self.frame += 1

        for s in self.stars:
            s[1] += s[2]
            if s[1] > H:
                s[0], s[1] = random.randint(0, W), 0

        if self.paused or self.game_over:
            return

        speed = 6
        if self.pressed("left", "a"):
            self.px -= speed
        if self.pressed("right", "d"):
            self.px += speed
        if self.pressed("up", "w"):
            self.py -= speed
        if self.pressed("down", "s"):
            self.py += speed
        self.px = max(20, min(W - 20, self.px))
        self.py = max(40, min(H - 30, self.py))

        if self.cooldown > 0:
            self.cooldown -= 1
        if self.pressed("space") and self.cooldown == 0:
            self.bullets.append([self.px, self.py - 22])
            self.cooldown = 10

        for b in self.bullets:
            b[1] -= 11
        self.bullets = [b for b in self.bullets if b[1] > -10]

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = max(12, 40 - self.score // 120)
            size = random.randint(14, 24)
            spd = random.uniform(2, 3.5) + self.score / 800
            self.enemies.append([random.randint(size, W - size), -size, spd, size])

        for en in self.enemies:
            en[1] += en[2]
        self.enemies = [en for en in self.enemies if en[1] < H + 40]

        for b in self.bullets[:]:
            for en in self.enemies[:]:
                if abs(b[0] - en[0]) < en[3] and abs(b[1] - en[1]) < en[3]:
                    self.bullets.remove(b)
                    self.enemies.remove(en)
                    self.explode(en[0], en[1])
                    self.score += 10
                    break

        if self.invincible > 0:
            self.invincible -= 1
        else:
            for en in self.enemies[:]:
                if abs(self.px - en[0]) < en[3] + 12 and abs(self.py - en[1]) < en[3] + 12:
                    self.enemies.remove(en)
                    self.explode(self.px, self.py, 25)
                    self.lives -= 1
                    self.invincible = 90
                    if self.lives <= 0:
                        self.game_over = True
                    break

        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]

    def draw(self):
        c = self.canvas
        c.delete("all")

        for x, y, spd in self.stars:
            col = {1: "#444466", 2: "#8888aa", 3: "#ffffff"}[spd]
            c.create_rectangle(x, y, x + spd, y + spd, fill=col, outline="")

        for p in self.particles:
            r = p[4] / 10
            c.create_oval(p[0] - r, p[1] - r, p[0] + r, p[1] + r, fill="#ffaa33", outline="")

        for x, y in self.bullets:
            c.create_rectangle(x - 2, y - 8, x + 2, y + 8, fill="#66ffff", outline="")

        for x, y, _, s in self.enemies:
            c.create_polygon(x - s, y - s, x + s, y - s, x, y + s,
                             fill="#ff4466", outline="#ffaaaa", width=2)

        if not self.game_over and (self.invincible == 0 or self.frame % 6 < 3):
            x, y = self.px, self.py
            c.create_polygon(x, y - 22, x - 18, y + 16, x, y + 8, x + 18, y + 16,
                             fill="#44ddff", outline="#ffffff", width=2)

        # HUD
        c.create_text(10, 10, anchor="nw", fill="white",
                      font=("Consolas", 14, "bold"), text=f"Score: {self.score}")
        c.create_text(W - 10, 10, anchor="ne", fill="#ff6688",
                      font=("Consolas", 14, "bold"), text="Lives: " + "♥ " * self.lives)

        if self.paused:
            c.create_text(W / 2, H / 2, fill="white", font=("Consolas", 28, "bold"),
                          text="PAUSED")
        if self.game_over:
            c.create_text(W / 2, H / 2 - 20, fill="#ff4466", font=("Consolas", 32, "bold"),
                          text="GAME OVER")
            c.create_text(W / 2, H / 2 + 25, fill="white", font=("Consolas", 14),
                          text=f"Final score: {self.score}   |   Press R to restart")

    def loop(self):
        self.update()
        self.draw()
        self.root.after(FPS_MS, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()