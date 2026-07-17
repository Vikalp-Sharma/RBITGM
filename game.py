#!/usr/bin/env python3
"""
Rabbit Racer v7 — Complete clean rewrite. All bugs fixed.
Controls : Mouse=steer | LMB=accelerate | RMB=brake | [P]=pause
Cheat    : Middle-click x5 then scroll-up
"""
import pygame, sys, random, math, os, json, subprocess

if "DISPLAY" not in os.environ and sys.platform not in ("win32","darwin"):
    os.environ.setdefault("DISPLAY",":0")

pygame.init()
try:    pygame.mixer.init(22050,-16,1,512); HAS_SND=True
except: HAS_SND=False
PG2  = pygame.version.vernum[0] >= 2
_HWR = hasattr(pygame,"WINDOWRESIZED")

# ── Logical canvas (height fixed, width dynamic) ─────────────
GAME_H   = 360
_LANE_PX = 52
_SW_MIN  = 26
_MAX_LN  = 10

GAME_W  = 240
N_LANES = 3
ROAD_L  = 42
ROAD_R  = 198
LANE_W  = _LANE_PX
LANES   = [ROAD_L+_LANE_PX*i+_LANE_PX//2 for i in range(3)]
canvas  = pygame.Surface((GAME_W,GAME_H))

screen = pygame.display.set_mode((720,1080),pygame.RESIZABLE)
pygame.display.set_caption("Rabbit Racer")
clock  = pygame.time.Clock()
FPS    = 60

# ── Dynamic layout ───────────────────────────────────────────
def recompute(win_w,win_h,gs=None):
    global GAME_W,N_LANES,ROAD_L,ROAD_R,LANE_W,LANES,canvas
    ww=max(1,win_w); wh=max(1,win_h)
    sc=max(0.5,wh/GAME_H)
    new_w=max(240,int(ww/sc))
    if new_w==GAME_W: return
    old_rl,old_rw,old_gw=ROAD_L,ROAD_R-ROAD_L,GAME_W
    GAME_W=new_w
    n=max(3,min(_MAX_LN,(GAME_W-2*_SW_MIN)//_LANE_PX))
    N_LANES=n; LANE_W=_LANE_PX
    rw=n*LANE_W; ROAD_L=(GAME_W-rw)//2; ROAD_R=ROAD_L+rw
    LANES=[ROAD_L+LANE_W*i+LANE_W//2 for i in range(n)]
    canvas=pygame.Surface((GAME_W,GAME_H))
    if gs and old_rw>0:
        frac=(gs.player.x-old_rl)/old_rw
        gs.player.x=float(ROAD_L+frac*(ROAD_R-ROAD_L))
        gs.player.clamp()
        for e in gs.enemies:
            e.lane=min(e.lane,N_LANES-1); e.x=float(LANES[e.lane])
        for o in gs.coinlist+gs.powerups:
            o.x=o.x*GAME_W/old_gw
        gs.side_peds=[p for p in gs.side_peds if 0<p.x<GAME_W]
        for tl in gs.lights:  tl.x=float(ROAD_R+13)
        for zb in gs.zebras:  zb.x=float(ROAD_R+13)

recompute(720,1080)

# ── Render helpers ───────────────────────────────────────────
def _ri():
    ww,wh=screen.get_size(); ww=max(1,ww); wh=max(1,wh)
    sc=max(0.5,wh/GAME_H)
    ow,oh=int(GAME_W*sc),int(GAME_H*sc)
    return (ww-ow)//2,(wh-oh)//2,sc

def game_mouse():
    sx,sy=pygame.mouse.get_pos(); ox,oy,sc=_ri()
    return max(0,min(GAME_W,int((sx-ox)/sc))),max(0,min(GAME_H,int((sy-oy)/sc)))

def blit_screen(shx=0,shy=0):
    ox,oy,sc=_ri(); screen.fill((0,0,0))
    screen.blit(pygame.transform.scale(canvas,(int(GAME_W*sc),int(GAME_H*sc))),(ox+shx,oy+shy))

# ── Speed ────────────────────────────────────────────────────
SPD_BASE=2.2; SPD_MAX=7.5; SPD_ACCEL=0.18; SPD_BRAKE=0.30; SPD_COAST=0.05
ENM_MAX=3.0; STOP_D=34

# ── Palette ──────────────────────────────────────────────────
BLACK=(0,0,0);   WHITE=(255,255,255); RED=(210,50,50)
GREEN=(50,190,50);BLUE=(50,100,210);  YELLOW=(240,210,50)
ORANGE=(230,140,40);GRAY=(115,115,115);SKIN=(255,200,155)
PINK=(255,160,190);CREAM=(230,225,205);ROTT_C=(38,28,18)
ROTT_T=(130,95,42);ROAD_C=(78,78,78); SIDE_C=(148,138,122)
GRASS_C=(55,150,45);DK_RD=(50,50,50); CHEAT_C=(255,60,255)
HEADLT=(255,255,200)
PALETTES=[
    [(200,50,50),(50,50,200),(50,180,50),(200,180,50),(160,50,180)],
    [(220,100,40),(80,50,200),(50,200,200),(180,50,180),(220,220,70)],
    [(220,220,220),(55,55,55),(200,150,50),(100,180,50),(50,150,200)],
    [(255,110,40),(110,40,255),(40,255,180),(255,40,110),(200,255,40)],
    [(255,200,80),(80,200,255),(200,80,255),(80,255,120),(255,80,180)],
]
def _dk(c,a=55): return tuple(max(0,v-a) for v in c)
def _lt(c,a=60): return tuple(min(255,v+a) for v in c)

# ── Font — Font(None) only; SysFont breaks PyInstaller ───────
_FC={}
def _F(sz):
    sz=max(8,int(sz))
    if sz not in _FC: _FC[sz]=pygame.font.Font(None,sz)
    return _FC[sz]

def T(d,text,x,y,col,sz=9):
    """Pixel text. Coords always int — no crash."""
    s=_F(sz).render(str(text),False,col); d.blit(s,(int(x),int(y))); return s.get_width()

def TC(d,text,y,col,sz=9):
    s=_F(sz).render(str(text),False,col); d.blit(s,(GAME_W//2-s.get_width()//2,int(y)))

# ── Sounds ───────────────────────────────────────────────────
def _beep(f=440,ms=50,v=0.13,sq=False):
    if not HAS_SND: return None
    try:
        n=int(22050*ms/1000)
        b=bytes([200 if(i*f//22050)%2==0 else 55 for i in range(n)] if sq else
                [int(127+127*math.sin(2*math.pi*f*i/22050)) for i in range(n)])
        s=pygame.mixer.Sound(buffer=b); s.set_volume(v); return s
    except: return None
SND_COIN=_beep(880,40,.11); SND_HIT=_beep(110,85,.18,True)
SND_LVL=_beep(660,120,.13); SND_BONUS=_beep(1046,55,.13)
def _play(s):
    if s:
        try: s.play()
        except: pass

# ── High score ───────────────────────────────────────────────
_SAVE=os.path.join(os.path.expanduser("~"),".rbitgm.json")
def hi_load():
    try:
        with open(_SAVE) as f: return json.load(f).get("hi",0)
    except: return 0
def hi_save(v):
    try:
        with open(_SAVE,"w") as f: json.dump({"hi":v},f)
    except: pass

# ── Uninstaller ──────────────────────────────────────────────
def launch_uninstall():
    cmd="sudo apt-get remove -y rabbit-racer ; echo Done. && sleep 2"
    for parts in [["lxterminal","-e"],["xterm","-e"],["x-terminal-emulator","-e"],
                  ["xfce4-terminal","--command"],["gnome-terminal","--"],["konsole","-e"]]:
        try:
            subprocess.Popen(parts+["bash","-c",cmd]); pygame.quit(); sys.exit()
        except (FileNotFoundError,OSError): continue
    try: subprocess.Popen(["sudo","apt-get","remove","-y","rabbit-racer"])
    except: pass
    pygame.quit(); sys.exit()

# ── Buttons ──────────────────────────────────────────────────
class Btn:
    def __init__(self,label,bx,by,bw,bh,bg,fg=WHITE):
        self.label=label; self.r=pygame.Rect(bx,by,bw,bh); self.bg=bg; self.fg=fg
    def draw(self,d):
        pygame.draw.rect(d,self.bg,self.r); pygame.draw.rect(d,WHITE,self.r,1)
        s=_F(9).render(self.label,False,self.fg)
        d.blit(s,(self.r.centerx-s.get_width()//2,self.r.centery-s.get_height()//2))
    def hit(self,gx,gy): return self.r.collidepoint(gx,gy)

def _mk_btns():
    bw,bh=90,16; bx=GAME_W//2-bw//2
    return (Btn("PLAY AGAIN",bx,GAME_H//2+44,bw,bh,(35,130,35)),
            Btn("UNINSTALL", bx,GAME_H//2+64,bw,bh,(130,30,30)),
            Btn("UNINSTALL", bx,GAME_H//2+24,bw,bh,(130,30,30)))
_BPLAY,_BUNI_O,_BUNI_P=_mk_btns()

# ─────────────────────────────────────────────────────────────
#  ROAD
# ─────────────────────────────────────────────────────────────
def draw_road(d,offset,night=False):
    rc=DK_RD if night else ROAD_C
    sc=(72,68,58) if night else SIDE_C
    gc=(24,82,24) if night else GRASS_C
    pygame.draw.rect(d,gc,(0,0,8,GAME_H)); pygame.draw.rect(d,gc,(GAME_W-8,0,8,GAME_H))
    pygame.draw.rect(d,sc,(8,0,ROAD_L-8,GAME_H)); pygame.draw.rect(d,sc,(ROAD_R,0,GAME_W-ROAD_R-8,GAME_H))
    kb=(50,46,38) if night else (100,92,80)
    pygame.draw.rect(d,kb,(ROAD_L-5,0,5,GAME_H)); pygame.draw.rect(d,kb,(ROAD_R,0,5,GAME_H))
    pygame.draw.rect(d,rc,(ROAD_L,0,ROAD_R-ROAD_L,GAME_H))
    pygame.draw.rect(d,WHITE,(ROAD_L,0,3,GAME_H)); pygame.draw.rect(d,WHITE,(ROAD_R-3,0,3,GAME_H))
    DH,GAP=14,8; TOT=DH+GAP; dy=int(offset)%TOT
    for ln in range(1,N_LANES):
        lx=ROAD_L+LANE_W*ln-1; y=-dy
        while y<GAME_H: pygame.draw.rect(d,YELLOW,(lx,y,2,DH)); y+=TOT
    jc=(54,50,42) if night else (96,88,76)
    for y0 in range(0,GAME_H,16):
        yo=(y0-int(offset)%16)%GAME_H
        pygame.draw.rect(d,jc,(8,yo,ROAD_L-8,1)); pygame.draw.rect(d,jc,(ROAD_R,yo,GAME_W-ROAD_R-8,1))
    bl=(22,85,18) if night else (32,115,25)
    for y0 in range(0,GAME_H,20):
        yo=(y0-int(offset)%20)%GAME_H
        for gx in(2,5): pygame.draw.rect(d,bl,(gx,yo,1,4))
        for gx in(GAME_W-3,GAME_W-6): pygame.draw.rect(d,bl,(gx,yo,1,4))

# ─────────────────────────────────────────────────────────────
#  CARS
# ─────────────────────────────────────────────────────────────
_DIMS=[(16,24),(18,28),(14,22),(18,26),(20,24),(16,26),(20,28)]

def draw_car(d,cx,cy,color,ctype=0,flip=False,hl=False):
    cx,cy=int(cx),int(cy)
    w,h=_DIMS[min(ctype,len(_DIMS)-1)]; bx,by=cx-w//2,cy-h//2
    dk=_dk(color); lt=_lt(color)
    hlc=HEADLT if hl else (255,255,120); tlc=(255,55,55); wc=(140,205,255)
    pygame.draw.rect(d,color,(bx,by+4,w,h-8)); pygame.draw.rect(d,dk,(bx+3,by+8,w-6,h-16))
    if flip:
        pygame.draw.rect(d,wc,(bx+4,by+h-13,w-8,4)); pygame.draw.rect(d,wc,(bx+4,by+8,w-8,4))
        pygame.draw.rect(d,tlc,(bx+2,by,4,3)); pygame.draw.rect(d,tlc,(bx+w-6,by,4,3))
        pygame.draw.rect(d,hlc,(bx+2,by+h-3,4,3)); pygame.draw.rect(d,hlc,(bx+w-6,by+h-3,4,3))
    else:
        pygame.draw.rect(d,wc,(bx+4,by+8,w-8,4)); pygame.draw.rect(d,wc,(bx+4,by+h-13,w-8,4))
        pygame.draw.rect(d,hlc,(bx+2,by,4,3)); pygame.draw.rect(d,hlc,(bx+w-6,by,4,3))
        pygame.draw.rect(d,tlc,(bx+2,by+h-3,4,3)); pygame.draw.rect(d,tlc,(bx+w-6,by+h-3,4,3))
    for wx,wy in[(bx-2,by+5),(bx+w-2,by+5),(bx-2,by+h-12),(bx+w-2,by+h-12)]:
        pygame.draw.rect(d,(20,20,20),(wx,wy,4,7)); pygame.draw.rect(d,GRAY,(wx+1,wy+2,2,3))
    pygame.draw.rect(d,lt,(bx+1,by+6,2,h-12))

def draw_player(d,cx,cy,night=False,braking=False):
    cx,cy=int(cx),int(cy)
    color=(215,45,45); w,h=20,28; bx,by=cx-w//2,cy-h//2
    dk=(145,18,18); lt=(255,105,105)
    pygame.draw.rect(d,color,(bx,by+4,w,h-8)); pygame.draw.rect(d,dk,(bx+3,by+8,w-6,h-16))
    pygame.draw.rect(d,(165,220,255),(bx+4,by+8,w-8,4))
    pygame.draw.rect(d,(165,220,255),(bx+4,by+h-13,w-8,4))
    hlc=HEADLT if night else (255,255,120)
    tlc=(255,10,10) if braking else (195,25,25)
    pygame.draw.rect(d,hlc,(bx+2,by,4,3)); pygame.draw.rect(d,hlc,(bx+w-6,by,4,3))
    pygame.draw.rect(d,tlc,(bx+2,by+h-3,4,3)); pygame.draw.rect(d,tlc,(bx+w-6,by+h-3,4,3))
    for wx,wy in[(bx-2,by+5),(bx+w-2,by+5),(bx-2,by+h-12),(bx+w-2,by+h-12)]:
        pygame.draw.rect(d,(20,20,20),(wx,wy,4,7)); pygame.draw.rect(d,GRAY,(wx+1,wy+2,2,3))
    pygame.draw.rect(d,lt,(bx+1,by+6,2,h-12))
    pygame.draw.rect(d,WHITE,(bx+5,by+h-4,w-10,3)); pygame.draw.rect(d,(50,50,200),(bx+6,by+h-3,w-12,1))
    # Rabbit driver
    rx,ry=cx-4,cy-3
    pygame.draw.rect(d,CREAM,(rx-1,ry-14,2,8)); pygame.draw.rect(d,CREAM,(rx+2,ry-14,2,8))
    pygame.draw.rect(d,PINK,(rx,ry-13,1,6)); pygame.draw.rect(d,PINK,(rx+3,ry-13,1,6))
    pygame.draw.rect(d,CREAM,(rx-2,ry-8,6,6))
    pygame.draw.rect(d,(185,38,38),(rx,ry-7,1,1)); pygame.draw.rect(d,(185,38,38),(rx+3,ry-7,1,1))
    pygame.draw.rect(d,PINK,(rx+1,ry-6,2,1))
    pygame.draw.rect(d,BLUE,(rx-2,ry-2,5,5)); pygame.draw.rect(d,WHITE,(rx-1,ry-1,3,3))
    # Rottweiler
    dx,d2=cx+4,cy-3
    pygame.draw.rect(d,ROTT_C,(dx-4,d2-9,2,3)); pygame.draw.rect(d,ROTT_C,(dx+3,d2-9,2,3))
    pygame.draw.rect(d,ROTT_C,(dx-3,d2-9,6,5))
    pygame.draw.rect(d,ROTT_T,(dx-2,d2-8,4,2)); pygame.draw.rect(d,ROTT_T,(dx-2,d2-5,4,2))
    pygame.draw.rect(d,(175,135,38),(dx-2,d2-8,1,1)); pygame.draw.rect(d,(175,135,38),(dx+1,d2-8,1,1))
    pygame.draw.rect(d,ROTT_C,(dx-3,d2-4,6,5)); pygame.draw.rect(d,ROTT_T,(dx-1,d2-3,3,3))

# ─────────────────────────────────────────────────────────────
#  WORLD OBJECTS
# ─────────────────────────────────────────────────────────────
def draw_stop_sign(d,cx,cy):
    cx,cy=int(cx),int(cy)
    pygame.draw.rect(d,(120,120,120),(cx-1,cy+7,3,14))
    pygame.draw.rect(d,RED,(cx-7,cy-6,14,13)); pygame.draw.rect(d,RED,(cx-5,cy-9,10,19))
    pygame.draw.rect(d,WHITE,(cx-5,cy-4,10,9)); pygame.draw.rect(d,WHITE,(cx-3,cy-6,6,13))
    pygame.draw.rect(d,RED,(cx-4,cy-3,8,7)); pygame.draw.rect(d,RED,(cx-2,cy-5,4,11))
    T(d,"STOP",cx-8,cy-2,WHITE,8)

def draw_tlight(d,cx,cy,state,night=False):
    """Night glow uses Surface+SRCALPHA — NO canvas.get_at/set_at."""
    cx,cy=int(cx),int(cy)
    pygame.draw.rect(d,(100,100,100),(cx-1,cy+22,3,22))
    pygame.draw.rect(d,(18,18,18),(cx-7,cy-22,14,45))
    pygame.draw.rect(d,(32,32,32),(cx-6,cy-21,12,43))
    for yo in(-19,-8,3): pygame.draw.rect(d,(10,10,10),(cx-7,cy+yo,14,2))
    lits=[(220,40,40),(230,195,28),(35,210,35)]
    dims=[(28,4,4),(38,34,4),(4,36,4)]
    yofs=[-18,-7,4]
    for i,(lit,dim,yo) in enumerate(zip(lits,dims,yofs)):
        c=lit if state==i else dim
        pygame.draw.rect(d,c,(cx-5,cy+yo,10,9))
        if state==i: pygame.draw.rect(d,_lt(c,80),(cx-4,cy+yo+1,4,3))
    if night:
        gc=[(55,0,0),(50,45,0),(0,55,0)][state]
        glow=pygame.Surface((26,26),pygame.SRCALPHA)
        pygame.draw.ellipse(glow,(*gc,85),glow.get_rect())
        d.blit(glow,(cx-13,cy+yofs[state]+4-9))

def draw_zebra(d,y,night=False):
    y=int(y); c=(185,185,185) if night else WHITE
    for lx in range(ROAD_L,ROAD_R,14): pygame.draw.rect(d,c,(lx,y,7,11))

_SHIRTS=[(200,50,50),(50,50,200),(50,180,50),(220,180,50),(180,50,200),(50,200,200),(200,200,50)]
_SKINS=[SKIN,(205,160,105),(145,105,62),(255,225,185)]

def draw_ped(d,cx,cy,anim,skin,shirt):
    cx,cy=int(cx),int(cy); lo=[0,2,0,-2][anim%4]
    leg=(25,25,90)
    pygame.draw.rect(d,leg,(cx-2,cy+3,2,5+lo)); pygame.draw.rect(d,leg,(cx+1,cy+3,2,5-lo))
    pygame.draw.rect(d,(22,14,6),(cx-3,cy+7+lo,3,2)); pygame.draw.rect(d,(22,14,6),(cx+1,cy+7-lo,3,2))
    pygame.draw.rect(d,shirt,(cx-3,cy-4,7,7))
    pygame.draw.rect(d,skin,(cx-5,cy-3+lo,3,4)); pygame.draw.rect(d,skin,(cx+3,cy-3-lo,3,4))
    pygame.draw.rect(d,skin,(cx-2,cy-9,5,5))
    pygame.draw.rect(d,(60,30,6),(cx-3,cy-11,7,2)); pygame.draw.rect(d,(60,30,6),(cx-2,cy-13,5,3))
    pygame.draw.rect(d,BLACK,(cx-1,cy-8,1,1)); pygame.draw.rect(d,BLACK,(cx+2,cy-8,1,1))

def draw_pu(d,cx,cy,kind,tick):
    cx,cy=int(cx),int(cy); off=1 if(tick//4)%2 else 0
    COLS={"shield":(30,120,230),"slow":(170,60,240),"x2":(230,180,20)}
    LABS={"shield":"S","slow":"T","x2":"x2"}
    FGCO={"shield":WHITE,"slow":WHITE,"x2":BLACK}
    c=COLS.get(kind,GRAY)
    pygame.draw.rect(d,c,(cx-6,cy-6+off,12,11)); pygame.draw.rect(d,WHITE,(cx-6,cy-6+off,12,11),1)
    T(d,LABS.get(kind,"?"),cx-4,cy-4+off,FGCO.get(kind,WHITE),10)

# ─────────────────────────────────────────────────────────────
#  HUD / OVERLAYS
# ─────────────────────────────────────────────────────────────
def draw_hud(d,gs):
    bf=int(min(gs.cam_spd,SPD_MAX)/SPD_MAX*42)
    pygame.draw.rect(d,(32,32,32),(GAME_W-48,GAME_H-14,44,7))
    bc=(45,215,45) if gs.cam_spd<3.5 else (215,180,38) if gs.cam_spd<6 else (215,45,45)
    pygame.draw.rect(d,bc,(GAME_W-47,GAME_H-13,max(0,bf),5))
    T(d,f"{gs.cam_spd:.1f}",GAME_W-48,GAME_H-23,(175,175,175),8)
    T(d,f"SC:{gs.score:05d}",2,2,WHITE,9)
    T(d,f"C:{gs.coins}",2,12,YELLOW,9)
    T(d,f"L:{gs.level}",GAME_W-28,2,(100,255,100),9)
    T(d,f"HI:{gs.hi}",GAME_W-52,12,(180,180,255),8)
    for i in range(min(gs.lives,7)):
        hx=2+i*11; hy=23
        for ddx,ddy,dw in[(1,0,3),(5,0,3),(0,1,9),(1,4,7),(2,5,5),(3,6,3),(4,7,1)]:
            pygame.draw.rect(d,RED,(hx+ddx,hy+ddy,dw,1))
    if gs.x2_t>0:  T(d,"x2",2,34,YELLOW,8)
    if gs.slow_t>0: T(d,"SLW",2,43,(170,75,245),8)
    if gs.player.shield>0: TC(d,"SHIELD",2,(75,155,255),8)
    if gs.cheat:           TC(d,"CHEAT!",2,CHEAT_C,9)
    if gs.stop_warn>0:
        a=min(30,gs.stop_warn); wc=(255,int(255*a/30),int(255*a/30))
        TC(d,"RED LIGHT",GAME_H//2-8,wc,9)
        TC(d,"RMB=BRAKE",GAME_H//2+2,(200,200,200),8)
    if gs.lvlup_t>0: TC(d,f"LEVEL {gs.level}!",GAME_H//2-36,YELLOW,14)
    if gs.night: T(d,"NIGHT",GAME_W-34,GAME_H-28,(90,90,195),8)
    if gs.paused: TC(d,"PAUSED  [P]",GAME_H//2-6,WHITE,13)

def _ov(d,a=165):
    s=pygame.Surface((GAME_W,GAME_H),pygame.SRCALPHA); s.fill((0,0,0,a)); d.blit(s,(0,0))

def draw_gameover(d,gs):
    _ov(d)
    TC(d,"GAME OVER",GAME_H//2-60,RED,16)
    for i,(t,c) in enumerate([(f"SCORE  {gs.score:05d}",WHITE),(f"COINS  {gs.coins}",YELLOW),
                               (f"LEVEL  {gs.level}",(100,255,100)),(f"BEST   {gs.hi}",(180,180,255))]):
        TC(d,t,GAME_H//2-32+i*13,c,9)
    _BPLAY.draw(d); _BUNI_O.draw(d)

def draw_pause(d):
    _ov(d,145); TC(d,"PAUSED",GAME_H//2-50,WHITE,16)
    TC(d,"[P] RESUME",GAME_H//2-30,WHITE,9); _BUNI_P.draw(d)

def draw_title(d,off,hi):
    draw_road(d,off); _ov(d,178)
    TC(d,"RABBIT",44,YELLOW,19); TC(d,"RACER",64,YELLOW,19)
    draw_player(d,GAME_W//2,120)
    for y,(t,c) in zip([150,163,176,194,213],[
        ("MOUSE TO STEER",WHITE),("LMB=ACCEL  RMB=BRAKE",YELLOW),
        ("DODGE CARS + GRAB COINS",(180,255,180)),("CLICK TO START",(100,255,100)),
        (f"BEST: {hi}",(180,180,255))]):
        TC(d,t,y,c,9)
    TC(d,"CHEAT: MID-CLICK x5 + SCROLL UP",GAME_H-14,(95,95,195),7)

# ─────────────────────────────────────────────────────────────
#  PARTICLES / POPUPS / SKIDMARKS
# ─────────────────────────────────────────────────────────────
class Particle:
    __slots__=("x","y","vx","vy","life","ml","col","sz")
    def __init__(self,x,y,col,spd=2.5,life=22,sz=2):
        self.x=float(x);self.y=float(y);self.col=col;self.life=life;self.ml=life;self.sz=sz
        a=random.uniform(0,math.tau);s=random.uniform(.3,spd)
        self.vx=math.cos(a)*s;self.vy=math.sin(a)*s
    def tick(self): self.x+=self.vx;self.y+=self.vy;self.vy+=.10;self.life-=1
    def draw(self,d):
        sz=max(1,int(self.sz*self.life/self.ml))
        pygame.draw.rect(d,self.col[:3],(int(self.x),int(self.y),sz,sz))

class Popup:
    def __init__(self,x,y,t,col,big=False):
        self.x=float(x);self.y=float(y);self.t=t;self.col=col;self.life=42;self.ml=42;self.big=big
    def tick(self): self.y-=.55;self.life-=1
    def draw(self,d):
        s=_F(13 if self.big else 9).render(self.t,False,self.col)
        s.set_alpha(max(0,int(255*self.life/self.ml)));d.blit(s,(int(self.x)-s.get_width()//2,int(self.y)))

class Skidmark:
    """Stores int coords from init — blit always safe."""
    def __init__(self,x,y): self.x=int(x);self.y=int(y);self.life=110
    def tick(self,cs):
        # Accumulate float movement then convert to int
        self._yf=getattr(self,"_yf",float(self.y))+cs*0.25
        self.y=int(self._yf); self.life-=1
    def draw(self,d):
        a=max(0,min(110,self.life))
        s=pygame.Surface((4,8),pygame.SRCALPHA); s.fill((18,18,18,a))
        d.blit(s,(self.x-2,self.y))  # x,y are ints — no crash

# ─────────────────────────────────────────────────────────────
#  GAME OBJECTS
# ─────────────────────────────────────────────────────────────
class Player:
    W,H=20,28
    def __init__(self):
        self.x=float(GAME_W//2); self.y=float(GAME_H-82); self.shield=0
    def clamp(self):
        self.x=max(float(ROAD_L+self.W//2+4),min(float(ROAD_R-self.W//2-4),self.x))
    def steer(self,gmx):
        self.x+=(float(gmx)-self.x)*0.20; self.clamp()
        if self.shield>0: self.shield-=1
    def rect(self):
        return pygame.Rect(int(self.x)-self.W//2+4,int(self.y)-self.H//2+4,self.W-8,self.H-8)
    def draw(self,d,night=False,braking=False):
        draw_player(d,self.x,self.y,night,braking)
        if self.shield>0:
            sv=pygame.Surface((28,36),pygame.SRCALPHA)
            pygame.draw.rect(sv,(50,150,255,min(200,self.shield*5)),(0,0,28,36),2)
            d.blit(sv,(int(self.x)-14,int(self.y)-18))

class Enemy:
    def __init__(self,lvl,lane):
        self.lane=lane; self.x=float(LANES[min(lane,N_LANES-1)]); self.y=-34.0
        self.w,self.h=18,26
        pal=PALETTES[min(lvl-1,len(PALETTES)-1)]
        self.color=random.choice(pal); self.ctype=random.randint(0,min(lvl+1,6))
        top=min(2.2,0.7+(lvl-1)*0.06)
        self.base_spd=random.uniform(0.55,top)
        self.eff_spd=self.base_spd; self.stopped=False; self.stop_tmr=0; self.passed=False
    def tick(self,cam_spd,stop_lines,slow=False):
        front=self.y+self.h//2
        must=any(act and 0<(sly-front)<STOP_D+12 for sly,act in stop_lines)
        if must and not self.stopped:
            self.eff_spd=max(0.0,self.eff_spd-0.18)
            if self.eff_spd==0.0: self.stopped=True; self.stop_tmr=0
        elif self.stopped:
            self.stop_tmr+=1
            clear=all((not act) or (sly-front)>4 for sly,act in stop_lines)
            if clear or self.stop_tmr>320: self.stopped=False; self.eff_spd=self.base_spd
        else:
            self.eff_spd=min(self.base_spd,self.eff_spd+0.13)
        if not self.stopped:
            mv=min(ENM_MAX,self.eff_spd+cam_spd*0.18)*(0.5 if slow else 1.0)
            self.y+=mv
    def rect(self):
        return pygame.Rect(int(self.x)-self.w//2+3,int(self.y)-self.h//2+3,self.w-6,self.h-6)
    def draw(self,d,night=False): draw_car(d,self.x,self.y,self.color,self.ctype,True,night)

class Coin:
    def __init__(self):
        self.x=float(LANES[random.randint(0,N_LANES-1)]+random.randint(-8,8))
        self.y=-12.0; self.r=4; self.anim=0
    def tick(self,cs): self.y+=1.4+cs*0.38; self.anim=(self.anim+1)%8
    def rect(self): return pygame.Rect(int(self.x)-4,int(self.y)-4,8,8)
    def draw(self,d):
        cx,cy=int(self.x),int(self.y); off=1 if self.anim<4 else 0
        pygame.draw.rect(d,(208,188,42),(cx-3,cy-4+off,6,7))
        pygame.draw.rect(d,(255,238,96),(cx-2,cy-5+off,4,1)); pygame.draw.rect(d,(255,238,96),(cx-2,cy+2+off,4,1))
        pygame.draw.rect(d,(155,135,16),(cx-4,cy-2+off,1,3)); pygame.draw.rect(d,(155,135,16),(cx+3,cy-2+off,1,3))
        pygame.draw.rect(d,(148,126,12),(cx-1,cy-3+off,2,5))

class PowerUp:
    KINDS=["shield","slow","x2"]
    def __init__(self):
        self.kind=random.choice(self.KINDS)
        self.x=float(LANES[random.randint(0,N_LANES-1)]); self.y=-16.0; self.r=7; self.anim=0
    def tick(self,cs): self.y+=1.3+cs*0.35; self.anim+=1
    def rect(self): return pygame.Rect(int(self.x)-7,int(self.y)-7,14,14)
    def draw(self,d): draw_pu(d,self.x,self.y,self.kind,self.anim)

class StopSign:
    def __init__(self):
        self.x=float(random.choice([ROAD_L-14,ROAD_R+14])); self.y=float(random.randint(-90,-50))
    def tick(self,cs): self.y+=1.4+cs*0.36
    def draw(self,d): draw_stop_sign(d,self.x,self.y)

class TrafficLight:
    _D=[180,65,200]
    def __init__(self):
        self.x=float(ROAD_R+13); self.y=float(random.randint(-130,-80))
        self.state=0; self.tmr=random.randint(0,60)
    @property
    def sline(self): return self.y+22
    @property
    def active(self): return self.state in(0,1)
    def tick(self,cs):
        self.y+=cs; self.tmr+=1
        if self.tmr>=self._D[self.state]: self.state=(self.state+1)%3; self.tmr=0
    def draw(self,d,night=False):
        draw_tlight(d,self.x,self.y,self.state,night)
        if self.active:
            pygame.draw.rect(d,RED if self.state==0 else(215,175,28),(ROAD_L,int(self.sline),ROAD_R-ROAD_L,2))

class ZebraCrossing:
    _D=[200,60,170]
    def __init__(self):
        self.x=float(ROAD_R+13); self.y=float(random.randint(-160,-100))
        self.state=0; self.tmr=random.randint(0,80); self.peds=[]
    @property
    def cross_y(self): return self.y+20
    @property
    def sline(self): return self.y+18
    @property
    def active(self): return self.state in(0,1)
    def ped_on_road(self): return any(ROAD_L-4<p.x<ROAD_R+4 for p in self.peds)
    def tick(self,cs):
        prev=self.state; self.y+=cs; self.tmr+=1
        if self.tmr>=self._D[self.state]: self.state=(self.state+1)%3; self.tmr=0
        if prev!=0 and self.state==0:
            for i in range(random.randint(2,5)):
                self.peds.append(_ZPed(ROAD_R+18,self.cross_y+random.randint(-2,2),i*26))
        for p in self.peds[:]:
            p.tick(cs)
            if p.done: self.peds.remove(p)
    def draw(self,d,night=False):
        draw_zebra(d,self.cross_y,night)
        draw_tlight(d,self.x,self.y,self.state,night)
        if self.active:
            pygame.draw.rect(d,RED if self.state==0 else(215,175,28),(ROAD_L,int(self.sline),ROAD_R-ROAD_L,2))
        for p in self.peds: p.draw(d)

class _ZPed:
    def __init__(self,x,y,delay=0):
        self.x=float(x);self.y=float(y);self.delay=delay;self.done=False
        self.anim=0;self._a=0;self.shirt=random.choice(_SHIRTS);self.skin=random.choice(_SKINS)
    def tick(self,cs):
        self.y+=cs
        if self.delay>0: self.delay-=1; return
        self.x-=0.65;self._a+=1
        if self._a>=6: self.anim=(self.anim+1)%4;self._a=0
        if self.x<ROAD_L-24: self.done=True
    def draw(self,d):
        if self.delay>0: return
        draw_ped(d,self.x,self.y,self.anim,self.skin,self.shirt)

class SidePed:
    def __init__(self):
        side=random.choice([-1,1])
        if side==-1:
            lo=max(10,8); hi=max(lo+2,ROAD_L-8)
            self.xmin,self.xmax=float(lo),float(hi)
        else:
            lo=min(ROAD_R+6,GAME_W-12); hi=max(lo+2,GAME_W-9)
            self.xmin,self.xmax=float(lo),float(hi)
        self.x=float(random.randint(int(self.xmin),int(self.xmax)))
        self.y=float(random.randint(20,GAME_H-80))
        self.dir=random.choice([-1,1]); self.xspd=random.uniform(.28,.52)
        self.anim=0;self._a=0;self.done=False
        self.shirt=random.choice(_SHIRTS);self.skin=random.choice(_SKINS)
    def tick(self,cs):
        self.y+=cs; self.x+=self.xspd*self.dir
        if self.x<=self.xmin: self.x=self.xmin;self.dir=1
        if self.x>=self.xmax: self.x=self.xmax;self.dir=-1
        self._a+=1
        if self._a>=7: self.anim=(self.anim+1)%4;self._a=0
        if self.y>GAME_H+30: self.done=True
    def draw(self,d): draw_ped(d,self.x,self.y,self.anim,self.skin,self.shirt)

# ─────────────────────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────────────────────
class GS:
    def __init__(self,hi=0):
        self.score=0;self.coins=0;self.level=1;self.lives=3;self.hi=hi
        self.cam_spd=SPD_BASE;self.road_off=0.0;self.player=Player()
        self.enemies=[];self.coinlist=[];self.powerups=[]
        self.signs=[];self.lights=[];self.zebras=[];self.side_peds=[]
        self.particles=[];self.popups=[];self.skids=[]
        self.sp_t=0;self.co_t=0;self.pd_t=0;self.zb_t=0;self.lt_t=0;self.pu_t=0
        self.inv=0;self.flash=False;self.flash_t=0
        self.shk=0;self.sx=0;self.sy=0
        self.game_over=False;self.paused=False;self.lvlup_t=0
        self.stop_warn=0;self.x2_t=0;self.slow_t=0;self.night=False
        self.cheat=False;self._sc=0;self._sl=0;self._cs=0
        self._rl=[]

# ─────────────────────────────────────────────────────────────
#  CHEAT
# ─────────────────────────────────────────────────────────────
def cheat_ev(gs,ev):
    now=pygame.time.get_ticks()
    if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==2:
        if now-gs._sl>5000: gs._sc=0
        gs._sc+=1;gs._sl=now
        if gs._sc>=5: gs._cs=1
    sup=False
    if PG2 and ev.type==pygame.MOUSEWHEEL and ev.y>0: sup=True
    if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==4: sup=True
    if gs._cs==1 and sup:
        gs.cheat=not gs.cheat;gs._cs=0;gs._sc=0
        if gs.cheat:
            gs.coins+=999;gs.lives=99;gs.score+=9999;gs.player.shield=600
            gs.popups.append(Popup(GAME_W//2,GAME_H//2,"CHEAT ON!",CHEAT_C,True))
        else:
            gs.lives=min(gs.lives,3)  # reset excess lives
            gs.popups.append(Popup(GAME_W//2,GAME_H//2,"CHEAT OFF",WHITE,True))

# ─────────────────────────────────────────────────────────────
#  UPDATE
# ─────────────────────────────────────────────────────────────
def update(gs,gmx,lmb,rmb):
    if gs.paused: return
    gs.player.steer(gmx)
    slow=gs.slow_t>0
    sp_top=(SPD_MAX+(gs.level-1)*0.15)*(0.55 if slow else 1.0)
    if lmb and not rmb:   gs.cam_spd=min(sp_top,gs.cam_spd+SPD_ACCEL)
    elif rmb and not lmb: gs.cam_spd=max(0.0,gs.cam_spd-SPD_BRAKE)
    else:
        base=SPD_BASE*(0.55 if slow else 1.0)
        if   gs.cam_spd>base: gs.cam_spd=max(base,gs.cam_spd-SPD_COAST)
        elif gs.cam_spd<base: gs.cam_spd=min(base,gs.cam_spd+SPD_COAST)
    if gs.cheat: gs.cam_spd=min(gs.cam_spd,SPD_BASE+0.7)
    # Skid marks — capped + probabilistic, no flood
    if rmb and gs.cam_spd<SPD_BASE-0.2 and len(gs.skids)<40 and random.random()<0.25:
        for off in(-5,5): gs.skids.append(Skidmark(int(gs.player.x)+off,int(gs.player.y)+10))
    gs.road_off=(gs.road_off+gs.cam_spd)%100000
    gs.score+=1;gs.hi=max(gs.hi,gs.score);gs.night=(gs.level>=6)
    if gs.x2_t>0:  gs.x2_t-=1
    if gs.slow_t>0: gs.slow_t-=1
    if gs.lvlup_t>0: gs.lvlup_t-=1
    if gs.coins>=gs.level*12 and gs.level<50:
        gs.level+=1;gs.lvlup_t=48;_play(SND_LVL)
        gs.popups.append(Popup(GAME_W//2,GAME_H//2-20,f"LVL {gs.level}!",YELLOW,True))
    if gs.shk>0: gs.shk-=1;gs.sx=random.randint(-3,3);gs.sy=random.randint(-3,3)
    else: gs.sx=gs.sy=0
    stop_lines=[(tl.sline,tl.active) for tl in gs.lights]
    stop_lines+=[(zb.sline,zb.active and zb.ped_on_road()) for zb in gs.zebras]
    py=gs.player.y
    if any(act and py-65<sly<py+8 for sly,act in stop_lines): gs.stop_warn=max(gs.stop_warn,35)
    if gs.stop_warn>0: gs.stop_warn-=1
    # Spawn enemies
    gs.sp_t+=1
    sr=max(26,78-gs.level*5)
    if gs.sp_t>=sr:
        gs.sp_t=0
        avail=[l for l in range(N_LANES) if l not in gs._rl[-2:]]
        lane=random.choice(avail) if avail else random.randint(0,N_LANES-1)
        gs._rl.append(lane)
        if len(gs._rl)>5: gs._rl.pop(0)
        gs.enemies.append(Enemy(gs.level,lane))
    # Spawn coins
    gs.co_t+=1
    if gs.co_t>=68:
        gs.co_t=0; c=Coin()
        occ={int(e.x) for e in gs.enemies if abs(e.y+20)<50}
        if int(c.x) not in occ: gs.coinlist.append(c)
    # Spawn powerups
    gs.pu_t+=1
    if gs.pu_t>=370 and len(gs.powerups)<2: gs.pu_t=0;gs.powerups.append(PowerUp())
    # Side peds
    gs.pd_t+=1
    if gs.pd_t>=150:
        gs.pd_t=0
        if random.random()<0.6: gs.side_peds.append(SidePed())
    # Decorations
    if random.random()<0.004: gs.signs.append(StopSign())
    gs.lt_t+=1
    if gs.lt_t>=310 and len(gs.lights)<2: gs.lt_t=0;gs.lights.append(TrafficLight())
    gs.zb_t+=1
    if gs.zb_t>=470 and len(gs.zebras)<2: gs.zb_t=0;gs.zebras.append(ZebraCrossing())
    pr=gs.player.rect()
    # Enemies
    for e in gs.enemies[:]:
        e.tick(gs.cam_spd,stop_lines,gs.slow_t>0)
        if e.y>GAME_H+44: gs.enemies.remove(e); continue
        if not e.passed and e.y>gs.player.y+22: e.passed=True;gs.score+=10
        if gs.inv<=0 and e.rect().colliderect(pr):
            if gs.cheat or gs.player.shield>0: e.y-=8; continue
            gs.lives-=1;gs.inv=100;gs.flash_t=28;gs.shk=15;_play(SND_HIT)
            for _ in range(18):
                gs.particles.append(Particle(int(gs.player.x),int(gs.player.y),
                    random.choice([RED,ORANGE,YELLOW,WHITE])))
            if gs.lives<=0: gs.game_over=True;gs._cs=0;hi_save(gs.hi)
    # Coins
    mult=2 if gs.x2_t>0 else 1
    for c in gs.coinlist[:]:
        c.tick(gs.cam_spd)
        if c.y>GAME_H+22: gs.coinlist.remove(c); continue
        if c.rect().colliderect(pr):
            gain=50*mult;gs.coins+=mult;gs.score+=gain;_play(SND_COIN);gs.coinlist.remove(c)
            for _ in range(9):
                gs.particles.append(Particle(int(c.x),int(c.y),random.choice([YELLOW,(255,220,70)]),spd=1.8,life=18))
            gs.popups.append(Popup(int(c.x),int(c.y)-8,f"+{gain}",YELLOW))
    # Powerups
    for pu in gs.powerups[:]:
        pu.tick(gs.cam_spd)
        if pu.y>GAME_H+22: gs.powerups.remove(pu); continue
        if pu.rect().colliderect(pr):
            gs.powerups.remove(pu);_play(SND_BONUS)
            if pu.kind=="shield":   gs.player.shield=420;gs.popups.append(Popup(int(gs.player.x),int(gs.player.y)-20,"SHIELD!",BLUE,True))
            elif pu.kind=="slow":   gs.slow_t=360;gs.popups.append(Popup(int(gs.player.x),int(gs.player.y)-20,"SLOW TIME!",(170,75,245),True))
            elif pu.kind=="x2":     gs.x2_t=420;gs.popups.append(Popup(int(gs.player.x),int(gs.player.y)-20,"COINS x2!",YELLOW,True))
    for s in gs.signs[:]:
        s.tick(gs.cam_spd)
        if s.y>GAME_H+32: gs.signs.remove(s)
    for tl in gs.lights[:]:
        tl.tick(gs.cam_spd)
        if tl.y>GAME_H+60: gs.lights.remove(tl)
    for zb in gs.zebras[:]:
        zb.tick(gs.cam_spd)
        if zb.y>GAME_H+60: gs.zebras.remove(zb)
    for p in gs.side_peds[:]:
        p.tick(gs.cam_spd); 
        if p.done: gs.side_peds.remove(p)
    for sk in gs.skids[:]:
        sk.tick(gs.cam_spd)
        if sk.life<=0: gs.skids.remove(sk)
    for pt in gs.particles[:]:
        pt.tick()
        if pt.life<=0: gs.particles.remove(pt)
    for pp in gs.popups[:]:
        pp.tick()
        if pp.life<=0: gs.popups.remove(pp)
    if gs.inv>0: gs.inv-=1
    if gs.flash_t>0: gs.flash_t-=1;gs.flash=(gs.flash_t%6<3)
    else: gs.flash=False

# ─────────────────────────────────────────────────────────────
#  DRAW
# ─────────────────────────────────────────────────────────────
_rmb=False

def draw(gs):
    canvas.fill((10,10,20) if gs.night else BLACK)
    draw_road(canvas,gs.road_off,gs.night)
    for sk in gs.skids:      sk.draw(canvas)
    for s  in gs.signs:      s.draw(canvas)
    for zb in gs.zebras:     zb.draw(canvas,gs.night)
    for tl in gs.lights:     tl.draw(canvas,gs.night)
    for p  in gs.side_peds:  p.draw(canvas)
    for pu in gs.powerups:   pu.draw(canvas)
    for c  in gs.coinlist:   c.draw(canvas)
    for e  in gs.enemies:    e.draw(canvas,gs.night)
    for pt in gs.particles:  pt.draw(canvas)
    if not gs.flash:         gs.player.draw(canvas,gs.night,_rmb)
    for pp in gs.popups:     pp.draw(canvas)
    draw_hud(canvas,gs)
    if gs.game_over:  draw_gameover(canvas,gs)
    elif gs.paused:   draw_pause(canvas)

# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
def main():
    global screen,_rmb,_BPLAY,_BUNI_O,_BUNI_P
    hi=hi_load(); gs=None; title=True; off=0.0; tick=0

    def rbtn(): 
        global _BPLAY,_BUNI_O,_BUNI_P
        _BPLAY,_BUNI_O,_BUNI_P=_mk_btns()

    while True:
        clock.tick(FPS); tick+=1
        gmx,gmy=game_mouse()
        mb=pygame.mouse.get_pressed(); lmb=mb[0]; _rmb=mb[2]

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                if gs: hi_save(gs.hi)
                pygame.quit(); sys.exit()
            if ev.type==pygame.VIDEORESIZE:           # pygame 1.x
                screen=pygame.display.set_mode(ev.size,pygame.RESIZABLE)
                recompute(ev.w,ev.h,gs); rbtn()
            elif _HWR and ev.type==pygame.WINDOWRESIZED:  # pygame 2.x
                recompute(*screen.get_size(),gs); rbtn()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE:
                    if gs: hi_save(gs.hi)
                    pygame.quit(); sys.exit()
                if gs and not gs.game_over and ev.key==pygame.K_p:
                    gs.paused=not gs.paused
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if title:
                    gs=GS(hi); title=False
                elif gs and gs.game_over:
                    if _BPLAY.hit(gmx,gmy):   hi=gs.hi; gs=GS(hi)
                    elif _BUNI_O.hit(gmx,gmy): hi_save(gs.hi); launch_uninstall()
                elif gs and gs.paused:
                    if _BUNI_P.hit(gmx,gmy):  hi_save(gs.hi); launch_uninstall()
            if gs: cheat_ev(gs,ev)

        if title:
            off=(off+1.5)%100000; canvas.fill((14,14,32)); draw_title(canvas,off,hi)
        else:
            if not gs.game_over and not gs.paused: update(gs,gmx,lmb,_rmb)
            draw(gs)

        blit_screen(gs.sx if gs else 0, gs.sy if gs else 0)
        pygame.display.flip()

if __name__=="__main__":
    main()
