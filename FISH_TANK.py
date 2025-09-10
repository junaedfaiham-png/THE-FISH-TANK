from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18

import random, math, time
#JUNAED
# ---------------- Window / Camera ----------------
WIN_W, WIN_H = 1000, 800
ASPECT = WIN_W / WIN_H
fovY = 70

GRID_LENGTH = 1200
HALF = GRID_LENGTH*0.5
AQUARIUM_BOUNDS = HALF - 30.0
TOP_Z = 420.0

# Camera 
camera_pos = [0.0, 500.0, 520.0]
first_person = False  
camera_pitch = 0.0    

# ---------------- Gameplay State ----------------
class Hero:
    def __init__(self):
        self.x, self.y, self.z = 0.0, -150.0, 80.0
        self.yaw = 0.0
        self.speed = 240.0
        self.vert_speed = 160.0
        self.size = 50.0
        self.health = 100
        self.max_health = 100
        self.is_dead = False
        self.cheat = False
        self.last_dmg_time = 0.0

    def forward_vec(self):
        r = math.radians(self.yaw)
        return math.sin(r), math.cos(r)

    def move_dir(self, dx, dy, dt):
        if self.is_dead: return
        mag = math.hypot(dx, dy)
        if mag > 1e-6:
            dx /= mag; dy /= mag
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        clamp_to_aquarium(self)

    def move_vert(self, dz, dt):
        if self.is_dead: return
        self.z += dz * self.vert_speed * dt
        clamp_to_aquarium(self)

class Enemy:
    def __init__(self):
        ang = random.random() * 2*math.pi
        rad = GRID_LENGTH*0.45 + random.uniform(50,200)
        self.x = math.cos(ang)*rad
        self.y = math.sin(ang)*rad
        self.z = random.uniform(50, 280)
        self.speed = 90.0
        self.size = 26.0

        self.col = random.choice([(0.12,0.18,0.28),(0.10,0.20,0.18),(0.16,0.14,0.24),(0.18,0.22,0.30)])
        self.wander_dir = random.uniform(0, math.tau)
        self.wander_timer = random.uniform(1.0, 3.0)

    def wander(self, dt):
        self.wander_timer -= dt
        if self.wander_timer <= 0.0:
            self.wander_timer = random.uniform(0.8, 2.2)
            self.wander_dir += random.uniform(-0.6, 0.6)
        vx = math.sin(self.wander_dir) * (self.speed*0.6)
        vy = math.cos(self.wander_dir) * (self.speed*0.6)
        self.x += vx * dt
        self.y += vy * dt
        self.z += math.sin(self.wander_dir*0.7) * 18.0 * dt
        clamp_to_aquarium(self)

    def chase(self, hero, dt, difficulty_scale):
        to_hx = hero.x - self.x
        to_hy = hero.y - self.y
        to_hz = hero.z - self.z
        self.z += clamp(to_hz, -1, 1) * 40.0 * dt
        dist = math.sqrt(to_hx*to_hx + to_hy*to_hy) + 1e-6
        vx = (to_hx / dist) * self.speed * difficulty_scale
        vy = (to_hy / dist) * self.speed * difficulty_scale
        self.x += vx * dt
        self.y += vy * dt
        clamp_to_aquarium(self)

# Food & Deco
class Food:
    def __init__(self):
        self.x = random.uniform(-GRID_LENGTH*0.45, GRID_LENGTH*0.45)
        self.y = random.uniform(-GRID_LENGTH*0.45, GRID_LENGTH*0.45)
        self.base_z = random.uniform(60, 260)
        self.phase = random.random()*math.tau
        self.size = 10.0

    def pos(self, t):
        z = self.base_z + math.sin(t*1.3 + self.phase)*8.0
        return self.x, self.y, z

class Plant:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.height = random.uniform(50, 110)
        self.stalks = random.randint(3,6)
        self.phase = random.random()*math.tau

    def draw(self, t):
        glPushMatrix()
        glTranslatef(self.x, self.y, 0.0)
        quad = gluNewQuadric()
        for i in range(self.stalks):
            ang = (i/self.stalks)*math.tau + self.phase
            sway = math.sin(t*1.1 + ang)*8.0
            h = self.height * (0.8 + 0.4*random.random())
            glPushMatrix()
            glRotatef(sway, 0,1,0)
            glColor3f(0.10, 0.52, 0.14)
            gluCylinder(quad, 2.0, 0.8, h, 7, 1)
            glTranslatef(0,0,h)
            glColor3f(0.15, 0.7, 0.18)
            glutSolidSphere(3.5, 8, 8)
            glPopMatrix()
        glPopMatrix()

# Bubble system
class Bubble:
    def __init__(self, x, y, z=8.0, source='random', ox=None, oy=None):
        self.x, self.y, self.z = x, y, z
        self.v = random.uniform(24, 44)  # rise speed
        self.r = random.uniform(2.0, 5.0)
        self.phase = random.random()*math.tau
        self.source = source
        self.ox = ox if ox is not None else x
        self.oy = oy if oy is not None else y

    def update(self, dt):
        
        self.z += self.v * dt
        self.x += math.sin(self.z*0.02 + self.phase)*4.0*dt*10
        self.y += math.cos(self.z*0.018 + self.phase)*4.0*dt*10
        margin = 8.0
        self.x = clamp(self.x, -HALF+margin, HALF-margin)
        self.y = clamp(self.y, -HALF+margin, HALF-margin)
        if self.z > TOP_Z - 10.0:
            self.z = random.uniform(4.0, 16.0)
            if self.source == 'bubbler':
                self.x = self.ox + random.uniform(-2.5, 2.5)
                self.y = self.oy + random.uniform(-2.5, 2.5)
            elif self.source == 'plant':
                self.x = self.ox + random.uniform(-6, 6)
                self.y = self.oy + random.uniform(-6, 6)
            else: 
                self.x = random.uniform(-HALF*0.9, HALF*0.9)
                self.y = random.uniform(-HALF*0.9, HALF*0.9)

# Bubbler / Pump
BUB_POS = (HALF-80.0, -HALF+80.0, 0.0)
def draw_bubbler():
    x,y,z = BUB_POS
    glPushMatrix()
    glTranslatef(x,y,z)
    
    glColor3f(0.3,0.3,0.33)
    glPushMatrix()
    glScalef(20, 20, 6)
    glutSolidCube(1.0)
    glPopMatrix()
   
    glTranslatef(0, 0, 6.0)
    glRotatef(-90, 1,0,0)
    glColor3f(0.5,0.52,0.55)
    quad = gluNewQuadric()
    gluCylinder(quad, 2.0, 2.0, 20.0, 10, 1)
    glPopMatrix()

# Difficulty
DIFFS = ["EASY", "MEDIUM", "HARD"]
DIFF_SPEED_SCALE = [0.6, 1.0, 1.6]
DIFF_AGGRO_RANGE = [220.0, 280.0, 340.0]
diff_idx = 0

# Bunker (safe region)
BUNKER_CENTER = (220.0, -180.0)
BUNKER_RADIUS = 120.0
BUNKER_HEIGHT = 90.0
def hero_in_bunker(hero):
    dx = hero.x - BUNKER_CENTER[0]
    dy = hero.y - BUNKER_CENTER[1]
    on_xy = dx*dx + dy*dy <= BUNKER_RADIUS*BUNKER_RADIUS
    in_z = 0.0 <= hero.z <= BUNKER_HEIGHT
    return on_xy and in_z

# ---------------- Utility ----------------
def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def clamp_to_aquarium(obj):
    obj.x = clamp(obj.x, -AQUARIUM_BOUNDS, AQUARIUM_BOUNDS)
    obj.y = clamp(obj.y, -AQUARIUM_BOUNDS, AQUARIUM_BOUNDS)
    obj.z = clamp(obj.z, 20.0, TOP_Z-10.0)

def dist2(ax, ay, bx, by):
    return (ax-bx)*(ax-bx) + (ay-by)*(ay-by)

def dist3(ax, ay, az, bx, by, bz):
    return math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2)

# ---------------- Drawing helpers ----------------
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):

    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

#MAHIM
def draw_realistic_fish(size, base_col, t, enemy=False):
    """More 'real' fish: ellipsoid body, animated tail, side fins, eyes"""
    quad = gluNewQuadric()
    glPushMatrix()
    glScalef(1.6, 2.2, 1.0)  
    glColor3f(*base_col)     
    glutSolidSphere(size*0.25, 24, 18)
    glPopMatrix()


    wag = math.sin(t*7.0 + (0.0 if enemy else 1.2)) * 15.0
    glPushMatrix()
    glTranslatef(0, -size*0.75, 0)
    glRotatef(90, 1, 0, 0)
    glRotatef(wag, 0, 1, 0)
    glColor3f(base_col[0]*0.9, base_col[1]*0.9, base_col[2]*0.9)
    gluCylinder(quad, size*0.16, 0.0, size*0.8, 18, 1)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 0, size*0.35)
    glRotatef(-90, 1, 0, 0)
    glColor3f(base_col[0]*1.1, base_col[1]*1.1, base_col[2]*1.1)
    gluCylinder(quad, size*0.08, 0.0, size*0.30, 14, 1)
    glPopMatrix()

    for sgn in (-1, 1):
        glPushMatrix()
        glTranslatef(size*0.35*sgn, size*0.1, 0)
        flap = math.sin(t*5.0 + sgn)*18.0
        glRotatef(90, 0,1,0)
        glRotatef(flap, 0,0,1)
        glColor3f(base_col[0]*1.05, base_col[1]*1.05, base_col[2]*1.05)
        gluCylinder(quad, size*0.04, 0.0, size*0.30, 10, 1)
        glPopMatrix()

    
    for sgn in (-1, 1):
        glPushMatrix()
        glTranslatef(size*0.28*sgn, size*0.25, size*0.10)
        glColor3f(0.95, 0.95, 0.95)
        glutSolidSphere(size*0.06, 10, 10)
        glTranslatef(0, size*0.02, size*0.03)
        glColor3f(0.05, 0.05, 0.05)
        glutSolidSphere(size*0.03, 8, 8)
        glPopMatrix()

def draw_bunker():
    glPushMatrix()
    glTranslatef(BUNKER_CENTER[0], BUNKER_CENTER[1], 0.0)
    glRotatef(-90, 1, 0, 0)
    glColor3f(0.36, 0.30, 0.26)
    quad = gluNewQuadric()
    gluCylinder(quad, BUNKER_RADIUS, BUNKER_RADIUS*0.92, BUNKER_HEIGHT, 28, 1)
    glColor3f(0.46, 0.38, 0.30)
    gluDisk(quad, BUNKER_RADIUS*0.92, BUNKER_RADIUS, 28, 1)
    glPopMatrix()

sand_list = None
def build_sand():
    global sand_list
    random.seed(3)
    sand_list = glGenLists(1)
    glNewList(sand_list, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    s = HALF
    steps = 64
    for i in range(steps):
        for j in range(steps):
            x0 = -s + (i/steps)*GRID_LENGTH
            y0 = -s + (j/steps)*GRID_LENGTH
            x1 = -s + ((i+1)/steps)*GRID_LENGTH
            y1 = -s + ((j+1)/steps)*GRID_LENGTH
            def h(x,y):

                return 2.0*math.sin(x*0.01) + 1.5*math.cos(y*0.012) + 1.0*math.sin((x+y)*0.007)
            z00 = h(x0,y0); z10=h(x1,y0); z01=h(x0,y1); z11=h(x1,y1)

            glColor3f(0.86,0.82,0.67)
            glVertex3f(x0,y0,z00); glVertex3f(x1,y0,z10); glVertex3f(x1,y1,z11)

            glColor3f(0.84,0.80,0.65)
            glVertex3f(x0,y0,z00); glVertex3f(x1,y1,z11); glVertex3f(x0,y1,z01)
    glEnd()
    glEndList()

def draw_food_pellet():
    glColor3f(0.9, 0.22, 0.22)
    glutSolidSphere(6.0, 12, 12)

def draw_shield(radius):
    glColor4f(0.3, 0.8, 1.0, 0.22)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_CULL_FACE)  
    glutSolidSphere(radius, 18, 16)
    glEnable(GL_CULL_FACE)
    glDisable(GL_BLEND)

def draw_bubble(r):
    glColor4f(0.85, 0.93, 1.0, 0.35)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_CULL_FACE)  
    glutSolidSphere(r, 12, 10)
    glEnable(GL_CULL_FACE)
    glDisable(GL_BLEND)

# ---------------- Input ----------------
keys_down = set()
def keyboardListener(key, x, y):
    global first_person, diff_idx, hero
    k = key.decode("utf-8").lower() if isinstance(key, bytes) else key.lower()
    if k in ("w","a","s","d","q","e"):
        keys_down.add(k)
    elif k == "f":
        first_person = not first_person
    elif k == "c":
        hero.cheat = not hero.cheat
    elif k == "1":
        diff_idx = 0
    elif k == "2":
        diff_idx = 1
    elif k == "3":
        diff_idx = 2
    elif k == "r":
        reset_game()

def keyboardUp(key, x, y):
    k = key.decode("utf-8").lower() if isinstance(key, bytes) else key.lower()
    if k in keys_down:
        keys_down.discard(k)

def specialKeyListener(key, x, y):
    global camera_pos, camera_pitch, hero
    if first_person:

        if key == GLUT_KEY_LEFT:
            hero.yaw -= 5.0
        elif key == GLUT_KEY_RIGHT:
            hero.yaw += 5.0
        elif key == GLUT_KEY_UP:
            camera_pitch = clamp(camera_pitch + 3.0, -60.0, 60.0)
        elif key == GLUT_KEY_DOWN:
            camera_pitch = clamp(camera_pitch - 3.0, -60.0, 60.0)
    else:

        if key == GLUT_KEY_UP:
            camera_pos[1] -= 30
        elif key == GLUT_KEY_DOWN:
            camera_pos[1] += 30
        elif key == GLUT_KEY_LEFT:
            camera_pos[0] -= 30
        elif key == GLUT_KEY_RIGHT:
            camera_pos[0] += 30

def specialKeyUp(key, x, y):
    pass

# ---------------- Game Loop ----------------
hero = None
enemies = []
foods = []
plants = []
bubbles = []
last_spawn_food = 0.0
TARGET_FOODS = 30
last_time = None

def reset_game():
    global hero, enemies, foods, plants, bubbles, last_time, last_spawn_food, diff_idx, first_person, camera_pitch
    hero = Hero()
    enemies = [Enemy() for _ in range(14)]
    foods = [Food() for _ in range(TARGET_FOODS)]

    plants = []
    for _ in range(25):
        while True:
            x = random.uniform(-GRID_LENGTH*0.45, GRID_LENGTH*0.45)
            y = random.uniform(-GRID_LENGTH*0.45, GRID_LENGTH*0.45)
            if (x-BUNKER_CENTER[0])**2 + (y-BUNKER_CENTER[1])**2 > (BUNKER_RADIUS+40)**2:
                plants.append(Plant(x,y)); break

    bubbles = []
    for _ in range(60):  
        bubbles.append(Bubble(random.uniform(-HALF*0.9, HALF*0.9),
                              random.uniform(-HALF*0.9, HALF*0.9),
                              random.uniform(4.0, 60.0),
                              source='random'))
    for p in plants:    
        for _ in range(2):
            bubbles.append(Bubble(p.x + random.uniform(-6,6),
                                  p.y + random.uniform(-6,6),
                                  random.uniform(4.0, 16.0),
                                  source='plant', ox=p.x, oy=p.y))
    
    for _ in range(40):
        bubbles.append(Bubble(BUB_POS[0], BUB_POS[1],
                              random.uniform(4.0, 12.0),
                              source='bubbler', ox=BUB_POS[0], oy=BUB_POS[1]))
    last_time = None
    last_spawn_food = 0.0
    first_person = False
    camera_pitch = 0.0
    diff_idx = 1 

def setup_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    light_pos = (0.0, 0.0, 650.0, 1.0)
    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.9, 0.9, 0.95, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.25, 0.28, 0.32, 1.0))

def setupCamera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(fovY, ASPECT, 0.1, 6000.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    if first_person:
       
        yaw = math.radians(hero.yaw)
        pitch = math.radians(camera_pitch)
        dirx = math.cos(pitch) * math.sin(yaw)
        diry = math.cos(pitch) * math.cos(yaw)
        dirz = math.sin(pitch)
        eye = (hero.x, hero.y, hero.z + 14.0)
        at  = (hero.x + dirx*80.0, hero.y + diry*80.0, hero.z + 14.0 + dirz*80.0)
        gluLookAt(*eye, *at, 0, 0, 1)
    else:
        gluLookAt(camera_pos[0], camera_pos[1], camera_pos[2], 0, 0, 0, 0, 0, 1)

#Jerin 
def update(dt):
    global last_spawn_food, bubbles
    dx = dy = dz = 0.0
    if "w" in keys_down: dy += 1.0
    if "s" in keys_down: dy -= 1.0
    if "a" in keys_down: dx -= 1.0
    if "d" in keys_down: dx += 1.0
    if "q" in keys_down: dz += 1.0
    if "e" in keys_down: dz -= 1.0

    if abs(dx) + abs(dy) > 0:
        hero.yaw = math.degrees(math.atan2(dx, dy))

    hero.move_dir(dx, dy, dt)
    hero.move_vert(dz, dt)

    diff_scale = DIFF_SPEED_SCALE[diff_idx]
    aggro_r = DIFF_AGGRO_RANGE[diff_idx]
    for e in enemies:
        d2 = dist2(e.x, e.y, hero.x, hero.y)
        if d2 <= aggro_r*aggro_r:
            e.chase(hero, dt, diff_scale)
        else:
            e.wander(dt)

    min_sep = 35.0
    for i in range(len(enemies)):
        for j in range(i+1, len(enemies)):
            ei, ej = enemies[i], enemies[j]
            dx = ej.x - ei.x; dy = ej.y - ei.y
            d2 = dx*dx + dy*dy
            if d2 < (min_sep*min_sep) and d2 > 1e-4:
                d = math.sqrt(d2)
                push = (min_sep - d) * 0.5
                nx, ny = dx/d, dy/d
                ei.x -= nx*push; ei.y -= ny*push
                ej.x += nx*push; ej.y += ny*push
                clamp_to_aquarium(ei); clamp_to_aquarium(ej)

    if len(foods) < TARGET_FOODS and (time.time() - last_spawn_food) > 0.25:
        foods.append(Food()); last_spawn_food = time.time()

    now = time.time()
    i = 0
    while i < len(foods):
        fx, fy, fz = foods[i].pos(now)
        if dist3(hero.x, hero.y, hero.z, fx, fy, fz) < (hero.size*0.5 + foods[i].size):
            hero.health = min(hero.max_health, hero.health + 8)
            foods.pop(i)
        else:
            i += 1

    # Damage from enemies (unless shield/bunker)
    safe = hero.cheat or hero_in_bunker(hero)
    if not safe and (now - hero.last_dmg_time) > 0.35:
        for e in enemies:
            if dist3(hero.x, hero.y, hero.z, e.x, e.y, e.z) < (hero.size*0.5 + e.size*0.7):
                hero.health -= 5
                hero.last_dmg_time = now
                break
    if hero.health <= 0:
        hero.is_dead = True
        hero.health = 0

    for b in bubbles:
        b.update(dt)

    if random.random() < 0.06 and len(bubbles) < 260:
        bubbles.append(Bubble(random.uniform(-HALF*0.9, HALF*0.9),
                              random.uniform(-HALF*0.9, HALF*0.9),
                              4.0 + random.random()*20.0,
                              source='random'))
    if random.random() < 0.20 and len(bubbles) < 260:
        bubbles.append(Bubble(BUB_POS[0], BUB_POS[1], 6.0, source='bubbler', ox=BUB_POS[0], oy=BUB_POS[1]))

def drawHUD():
    glDisable(GL_LIGHTING)

    y1 = WIN_H - 26
    y2 = y1 - 20
    y3 = y2 - 20

    glColor3f(1,1,1)
    draw_text(WIN_W//2 - 160, y1, "[1] Easy   [2] Medium   [3] Hard")
    draw_text(WIN_W//2 - 40,  y2, f"Mode: {DIFFS[diff_idx]}")

    # Top-right: health
    glColor3f(0.95,0.25,0.25)
    draw_text(WIN_W - 180, y1, f"HEALTH: {hero.health:03d}")

    # Top-left: controls on two lines
    glColor3f(1,1,1)
    draw_text(12, y1, "Move: WASD + Q/E   Cam: Arrows")
    draw_text(12, y2, "FPV: F   Shield: C   Reset: R")

    if hero_in_bunker(hero):
        glColor3f(0.5,1.0,0.6)
        draw_text(WIN_W//2 - 70, y3, "IN BUNKER (SAFE)")
    if hero.is_dead:
        glColor3f(1,0.2,0.2)
        draw_text(WIN_W//2 - 120, WIN_H//2, "YOU DIED - Press R")

def draw_walls_transparent():
    #lass walls after everything else so contents are visible from outside.
    s = HALF
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_CULL_FACE)     #both sides
    glDepthMask(GL_FALSE)       
    glColor4f(0.5, 0.8, 1.0, 0.12)

    glBegin(GL_QUADS)

    glVertex3f(-s, s, 0); glVertex3f(s, s, 0); glVertex3f(s, s, TOP_Z); glVertex3f(-s, s, TOP_Z)

    glVertex3f(-s, -s, 0); glVertex3f(-s, -s, TOP_Z); glVertex3f(s, -s, TOP_Z); glVertex3f(s, -s, 0)

    glVertex3f(s, -s, 0); glVertex3f(s, -s, TOP_Z); glVertex3f(s, s, TOP_Z); glVertex3f(s, s, 0)

    glVertex3f(-s, -s, 0); glVertex3f(-s, s, 0); glVertex3f(-s, s, TOP_Z); glVertex3f(-s, -s, TOP_Z)
    glEnd()

    glDepthMask(GL_TRUE)
    glEnable(GL_CULL_FACE)
    glDisable(GL_BLEND)

def draw_scene():

    glCallList(sand_list)

   
    draw_bunker()


    draw_bubbler()

   
    t = time.time()
    for p in plants:
        p.draw(t)

  
    for f in foods:
        x,y,z = f.pos(t)
        glPushMatrix()
        glTranslatef(x,y,z)
        draw_food_pellet()
        glPopMatrix()

   
    for e in enemies:
        glPushMatrix()
        glTranslatef(e.x, e.y, e.z)
        yaw = math.degrees(math.atan2(hero.x-e.x, hero.y-e.y))
        glRotatef(yaw, 0,0,1)
        draw_realistic_fish(e.size, e.col, t, enemy=True)
        glPopMatrix()


    if not first_person:
        glPushMatrix()
        glTranslatef(hero.x, hero.y, hero.z)
        glRotatef(hero.yaw, 0,0,1)
        draw_realistic_fish(hero.size, (0.95,0.55,0.25), t)
        if hero.cheat:
            draw_shield(hero.size*0.85)
        glPopMatrix()
    else:
        if hero.cheat:
            # shield at hero in FPV so it's visible around camera
            glPushMatrix()
            glTranslatef(hero.x, hero.y, hero.z + 14.0)
            draw_shield(hero.size*0.9)
            glPopMatrix()

    # Bubbles (semi-transparent)
    for b in bubbles[-220:]:  # cap drawing count
        glPushMatrix()
        glTranslatef(b.x, b.y, b.z)
        draw_bubble(b.r)
        glPopMatrix()

def idle():
    global last_time
    now = time.time()
    dt = 0.016 if last_time is None else clamp(now - last_time, 0.0, 0.05)
    last_time = now
    if not hero.is_dead:
        update(dt)
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, WIN_W, WIN_H)
    setupCamera()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    setup_lighting()

    #opaque-ish scene
    draw_scene()

    #transparent glass walls
    draw_walls_transparent()

    # HUD
    glDisable(GL_LIGHTING)
    drawHUD()

    glutSwapBuffers()

def initGL():
    glClearColor(0.05, 0.15, 0.25, 1.0)  
    glEnable(GL_DEPTH_TEST)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Aquarium Hero Fish (v3)")

    initGL()
    build_sand()
    reset_game()

    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUp)
    glutSpecialFunc(specialKeyListener)
    glutSpecialUpFunc(specialKeyUp)

    glutMainLoop()

if __name__ == "__main__":
    main()

