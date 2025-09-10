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
