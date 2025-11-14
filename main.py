import os
import sys
import random
import asyncio
import pygame
from pygame.locals import *
import json


WINDOW_SIZE = 1000,1000
BOARD_SIZE = 800, 800
GRID_COLS = 9
GRID_ROWS = 9
CELL_SIZE = BOARD_SIZE[0] // GRID_COLS
BOARD_OFFSET = ((WINDOW_SIZE[0] - BOARD_SIZE[0]) // 2, (WINDOW_SIZE[1] - BOARD_SIZE[1]) // 2)
FPS = 60
SNAKE_STEP_DELAY_MS = 120

MENU, PLAYING, GAME_OVER = 0, 1, 2
game_state = MENU
DIFFICULTY_SETTINGS = {
    "Easy": 150,
    "Normal": 110,
    "Hard": 60,
    "Free Play": None
}
current_difficulty = None
timer_duration = None
timer_start = None

font_path = os.path.join("fonts","orbitron-black.otf")

POP_FOLDER = os.path.join("pops")
BUBBLE_FOLDER = os.path.join("bubbles") 
BUBBLE_NAMES = [f"bubble{i}" for i in range(1, 10)]
SPECIAL_BUBBLE_INDEX = 6
SPECIAL_BUBBLE2_INDEX = 7
SPECIAL_BUBBLE3_INDEX = 8
IMG_EXTS = [".png", ".jpg", ".jpeg"]
POWERUP_FOLDERS =[os.path.join("power up"), os.path.join("bombs")]
SNAKE_NAME = "snake"
SNAKE_INDEX = None
BOMB_FOLDER = os.path.join("bombs")
BOMB_NAMES = ["bomb1", "bomb2", "bomb3"]

OVERLAY_PATHS = {
    "board": {
        1: os.path.join("bubbles", "overlay12.png"),
        2: os.path.join("bubbles", "overlay11.png"),
    },
    "top": {
        1: os.path.join("bubbles", "overlaybar1.png"),
        2: os.path.join("bubbles", "overlaybar.png"),
    },
    "menu": {
        1: os.path.join("bubbles", "menu3.png"),
        2: os.path.join("bubbles", "menu2.png"),
    },
}
OVERLAY_CACHE = {key: {} for key in OVERLAY_PATHS}

HIGHLIGHT_DELAY_MS = 600
FONT_NAME = None
SCORE_PER_CHAIN = 10

HIGHSCORE_FILE = os.path.join("highscores.txt")

BG_COLOR = (18, 18, 22)
GRID_BG = (30, 30, 36)
GRID_LINE = (48, 48, 56)
HL_COLOR_3 = (120, 200, 255)
HL_COLOR_4 = (120, 255, 120)
HL_COLOR_5PLUS = (255, 150, 80)
HL_BOMB = (255,100,100)
T_COLOR = (180,80,220)

SCORE_COLOR = (237, 211, 119)
GAMEOVER_COLOR = (255, 100, 110)
volume_color = (100, 200, 110)
mute = False

BOMB_SOUND_FILE = os.path.join("jsounds", "bomb.ogg")
FIVER_SOUND_FILE = os.path.join("jsounds", "fiver.ogg")
hurry_flash_timer = 0
timer_sound_file = os.path.join("jsounds", "timer1.ogg")
timer_sound_file1 = os.path.join("jsounds", "timer2.ogg")
button_sound_file = os.path.join("jsounds", "button.ogg")
snake_sound_file = os.path.join("jsounds", "snake.ogg")
skin = 1
IS_WEB = sys.platform == "emscripten"

def load_font_safe(path, size, label):
    try:
        return pygame.font.Font(path, size)
    except Exception as e:
        print(f"Font load failed for {label}: {e}")
        return pygame.font.Font(None, size)

def load_pop_sounds(audio_enabled=True):
    sounds = []
    if not audio_enabled or not pygame.mixer.get_init():
        return sounds
    if os.path.isdir(POP_FOLDER):
        for fname in os.listdir(POP_FOLDER):
            if fname.lower().endswith((".mp3", ".wav", ".ogg")):
                try:
                    sounds.append(pygame.mixer.Sound(os.path.join(POP_FOLDER, fname)))
                except Exception as e:
                    print("Error loading sound:", fname, e)
    return sounds

def get_highscore_file():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "highscores.txt")

def load_highscores():
    path = get_highscore_file()
    if not os.path.exists(path):
        return {diff: 0 for diff in DIFFICULTY_SETTINGS.keys()}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for diff in DIFFICULTY_SETTINGS.keys():
            data.setdefault(diff, 0)
        return data
    except Exception:
        return {diff: 0 for diff in DIFFICULTY_SETTINGS.keys()}

def save_highscore(difficulty, score):
    highscores = load_highscores()
    if score > highscores.get(difficulty, 0):
        highscores[difficulty] = score
        try:
            with open(get_highscore_file(), "w", encoding="utf-8") as f:
                json.dump(highscores, f)
        except Exception:
            pass

def load_bomb_images():
    imgs = []
    for name in BOMB_NAMES:
        img = None
        for ext in IMG_EXTS:
            candidate = os.path.join(BOMB_FOLDER, name + ext)
            if os.path.exists(candidate):
                try:
                    img = pygame.image.load(candidate).convert_alpha()
                    break
                except Exception:
                    pass
        if img is None:
            surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surf, (220, 80, 80), (8, 8, CELL_SIZE-16, CELL_SIZE-16), border_radius=8)
            imgs.append(surf)
        else:
            imgs.append(pygame.transform.smoothscale(img, (CELL_SIZE, CELL_SIZE)))
    return imgs

def load_snake_image():
    for base in POWERUP_FOLDERS:
        for ext in IMG_EXTS:
            candidate = os.path.join(base, SNAKE_NAME + ext)
            if os.path.exists(candidate):
                try:
                    img = pygame.image.load(candidate).convert_alpha()
                    return pygame.transform.smoothscale(img, (CELL_SIZE, CELL_SIZE))
                except Exception:
                    pass
    return None


def load_scaled_overlay(path, size):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    except Exception as e:
        print(f"Error loading overlay '{path}': {e}")
        return None


def preload_overlays(target_size):
    for key, variants in OVERLAY_PATHS.items():
        cached = OVERLAY_CACHE.setdefault(key, {})
        for skin_id, path in variants.items():
            if skin_id not in cached:
                cached[skin_id] = load_scaled_overlay(path, target_size)


def draw_menu(surface, font_big, font_medium, skin):
    draw_overlaytmenu(surface)
    if skin == 1:
        title = font_big.render("Difficulty", True, T_COLOR)
        title1 = font_medium.render("Press R To", True, T_COLOR)
        title2 = font_medium.render("Restart", True, T_COLOR)
    else:
        title = font_big.render("Difficulty", True, SCORE_COLOR)
        title1 = font_medium.render("Press R To", True, SCORE_COLOR)
        title2 = font_medium.render("Restart", True, SCORE_COLOR)
    rect = title.get_rect(center=(WINDOW_SIZE[0]//2, 300))
    surface.blit(title, rect)
    rect1 = title1.get_rect(center=(WINDOW_SIZE[0]//2, 750))
    surface.blit(title1, rect1)
    rect2 = title2.get_rect(center=(WINDOW_SIZE[0]//2, 790))
    surface.blit(title2, rect2)

    title3 = font_medium.render("Press", True, (30,30,30))
    title4 = font_medium.render("M to Mute", True, (30,30,30))
    rect3 = title3.get_rect(center=(WINDOW_SIZE[0]//2, 900))
    surface.blit(title3, rect3)
    rect4 = title4.get_rect(center=(WINDOW_SIZE[0]//2, 940))
    surface.blit(title4, rect4)

    buttons = []
    labels = ["Easy", "Normal", "Hard", "Free Play"]
    for i, text in enumerate(labels):
        btn_text = font_medium.render(text, True, (30,30,30))
        btn_rect = pygame.Rect(WINDOW_SIZE[0]//2 - 150, 350 + i*100, 300, 60)
        surface.blit(btn_text, btn_text.get_rect(center=btn_rect.center))
        buttons.append((btn_rect, text))

    return buttons

def draw_timer(surface, elapsed, duration, timer_color):
    if duration is None:
        width = WINDOW_SIZE[0] - 100
    else:
        remaining = max(0, duration - elapsed)
        fraction = remaining / duration
        width = int((WINDOW_SIZE[0] - 100) * fraction)

    bar_rect = pygame.Rect(50, WINDOW_SIZE[1] - 80, width, 20)
    pygame.draw.rect(surface, (timer_color), bar_rect, border_radius=2)

def add_time(seconds, timer_duration, timer_start):
    timer_start += seconds * (timer_duration*15 )
    if timer_duration:
        now = pygame.time.get_ticks()
        elapsed = (now - timer_start) // 1000
        remaining = timer_duration - elapsed
        if remaining > timer_duration:
            timer_start = now - (0 * 1000)
    return timer_start


def load_bubble_images():
    images = []
    for name in BUBBLE_NAMES:
        img = None
        for ext in IMG_EXTS:
            candidate = os.path.join(BUBBLE_FOLDER, name + ext)

            if os.path.exists(candidate):
                try:
                    img = pygame.image.load(candidate).convert_alpha()
                    break
                except Exception:
                    pass
        if img is None:
            surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            color = [random.randint(80, 230) for _ in range(3)]
            pygame.draw.circle(surf, color, (CELL_SIZE//2, CELL_SIZE//2), CELL_SIZE//2 - 8)
            images.append(surf)
        else:
            images.append(pygame.transform.smoothscale(img, (CELL_SIZE, CELL_SIZE)))
    return images

def load_all_images():
    global SNAKE_INDEX
    bubble_imgs = load_bubble_images()
    bomb_imgs   = load_bomb_images()
    images = bubble_imgs + bomb_imgs
    BOMB_INDICES = list(range(len(bubble_imgs), len(bubble_imgs) + len(bomb_imgs)))
    snake_img = load_snake_image()
    if snake_img is not None:
        images.append(snake_img)
        SNAKE_INDEX = len(images) - 1
    else:
        SNAKE_INDEX = None

    return images, BOMB_INDICES

def in_bounds(r, c):
    return 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS

def grid_to_px(r, c):
    x = BOARD_OFFSET[0] + c * CELL_SIZE
    y = BOARD_OFFSET[1] + r * CELL_SIZE
    return x, y

def random_cell(score=0):
    if score < 1000:
        return random.randrange(0, len(BUBBLE_NAMES) - 1)
    else:
        pool = list(range(len(BUBBLE_NAMES) - 1)) * 10
        pool.append(SPECIAL_BUBBLE_INDEX)
        return random.choice(pool)

def create_grid(no_start_matches=True):
    grid = [[pick_random_cell(0) for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

    if no_start_matches:
        while True:
            matches = find_all_matches_wild_any(grid)
            if not matches:
                break
            for group in matches:
                for (r, c) in group:
                    grid[r][c] = pick_random_cell()
    return grid

def pick_random_cell(score=0):
    total = len(BUBBLE_NAMES)
    specials = {SPECIAL_BUBBLE_INDEX}
    try:
        specials.add(SPECIAL_BUBBLE2_INDEX)
    except NameError:
        pass
    try:
        specials.add(SPECIAL_BUBBLE3_INDEX)
    except NameError:
        pass
    normals = [i for i in range(total) if i not in specials]
    pool = normals * 10
    if score >= 1000:
        pool.append(SPECIAL_BUBBLE_INDEX)
    if 'SPECIAL_BUBBLE2_INDEX' in globals() and score >= 6000:
        pool.append(SPECIAL_BUBBLE2_INDEX)
    if 'SPECIAL_BUBBLE3_INDEX' in globals() and score >= 8000:
        if random.random() < 0.25:
            pool.append(SPECIAL_BUBBLE3_INDEX)
    return random.choice(pool)


def find_all_matches(grid):
    groups = []
    for r in range(GRID_ROWS):
        c = 0
        while c < GRID_COLS:
            start = c
            val = grid[r][c]
            run = 1
            c += 1
            while c < GRID_COLS and grid[r][c] == val:
                run += 1
                c += 1
            if run >= 3 and val is not None and val != SPECIAL_BUBBLE_INDEX and (SNAKE_INDEX is None or val != SNAKE_INDEX) and (('SPECIAL_BUBBLE2_INDEX' not in globals()) or val != SPECIAL_BUBBLE2_INDEX):
                group = {(r, cc) for cc in range(start, start + run)}
                groups.append(group)

    for c in range(GRID_COLS):
        r = 0
        while r < GRID_ROWS:
            start = r
            val = grid[r][c]
            run = 1
            r += 1
            while r < GRID_ROWS and grid[r][c] == val:
                run += 1
                r += 1
            if run >= 3 and val is not None and val != SPECIAL_BUBBLE_INDEX and (SNAKE_INDEX is None or val != SNAKE_INDEX) and (('SPECIAL_BUBBLE2_INDEX' not in globals()) or val != SPECIAL_BUBBLE2_INDEX):
                group = {(rr, c) for rr in range(start, start + run)}
                groups.append(group)

    return groups

def find_all_matches_wild(grid):
    groups = []

    def is_wild(v):
        return 'SPECIAL_BUBBLE2_INDEX' in globals() and v == SPECIAL_BUBBLE2_INDEX

    def is_block(v):
        if v is None:
            return True
        if v == SPECIAL_BUBBLE_INDEX:
            return True
        if 'SNAKE_INDEX' in globals() and SNAKE_INDEX is not None and v == SNAKE_INDEX:
            return True
        return False

    for r in range(GRID_ROWS):
        c = 0
        while c < GRID_COLS:
            run = []
            base = None
            while c < GRID_COLS:
                v = grid[r][c]
                if is_block(v):
                    break
                if is_wild(v):
                    run.append((r, c))
                    c += 1
                    continue
                if base is None:
                    base = v
                    run.append((r, c))
                    c += 1
                    continue
                if v == base:
                    run.append((r, c))
                    c += 1
                else:
                    break
            if len(run) >= 3:
                groups.append(set(run))
            if not run:
                c += 1

    for c in range(GRID_COLS):
        r = 0
        while r < GRID_ROWS:
            run = []
            base = None
            while r < GRID_ROWS:
                v = grid[r][c]
                if is_block(v):
                    break
                if is_wild(v):
                    run.append((r, c))
                    r += 1
                    continue
                if base is None:
                    base = v
                    run.append((r, c))
                    r += 1
                    continue
                if v == base:
                    run.append((r, c))
                    r += 1
                else:
                    break
            if len(run) >= 3:
                groups.append(set(run))
            if not run:
                r += 1

    return groups

def find_all_matches_wild_any(grid):
    groups = []
    total = len(BUBBLE_NAMES)
    wild = SPECIAL_BUBBLE2_INDEX if 'SPECIAL_BUBBLE2_INDEX' in globals() else None

    def is_block(v):
        if v is None:
            return True
        if not isinstance(v, int):
            return True
        if v == SPECIAL_BUBBLE_INDEX:
            return True
        if 'SNAKE_INDEX' in globals() and SNAKE_INDEX is not None and v == SNAKE_INDEX:
            return True
        if 'SPECIAL_BUBBLE3_INDEX' in globals() and v == SPECIAL_BUBBLE3_INDEX:
            return True
        if v < 0 or v >= total:
            return True
        return False

    def is_wild(v):
        return wild is not None and v == wild

    bases = [i for i in range(total) if i != SPECIAL_BUBBLE_INDEX and (wild is None or i != wild)]
    for base in bases:
        for r in range(GRID_ROWS):
            c = 0
            while c < GRID_COLS:
                run = []
                while c < GRID_COLS:
                    v = grid[r][c]
                    if is_block(v):
                        break
                    if v == base or is_wild(v):
                        run.append((r, c))
                        c += 1
                    else:
                        break
                if len(run) >= 3:
                    groups.append(set(run))
                c = c + 1 if not run else c

    for base in bases:
        for c in range(GRID_COLS):
            r = 0
            while r < GRID_ROWS:
                run = []
                while r < GRID_ROWS:
                    v = grid[r][c]
                    if is_block(v):
                        break
                    if v == base or is_wild(v):
                        run.append((r, c))
                        r += 1
                    else:
                        break
                if len(run) >= 3:
                    groups.append(set(run))
                r = r + 1 if not run else r

    return groups

def has_any_match(grid):
    return len(find_all_matches_wild_any(grid)) > 0

def apply_gravity_and_refill(grid, score):
    for c in range(GRID_COLS):
        write_row = GRID_ROWS - 1
        for r in range(GRID_ROWS - 1, -1, -1):
            if grid[r][c] is not None:
                grid[write_row][c] = grid[r][c]
                write_row -= 1
        for r in range(write_row, -1, -1):
            grid[r][c] = pick_random_cell(score)

def would_match_after_swap(grid, r1, c1, r2, c2):
    a = grid[r1][c1]
    b = grid[r2][c2]

    if 'BOMB_INDICES' in globals() and (a in BOMB_INDICES or b in BOMB_INDICES):
        return True

    if grid[r1][c1] == SPECIAL_BUBBLE_INDEX or grid[r2][c2] == SPECIAL_BUBBLE_INDEX:
        return False

    if 'SPECIAL_BUBBLE3_INDEX' in globals():
        total = len(BUBBLE_NAMES)
        def is_normal(v):
            if v is None:
                return False
            if isinstance(v, int) and 0 <= v < total:
                if v == SPECIAL_BUBBLE_INDEX:
                    return False
                if 'SPECIAL_BUBBLE2_INDEX' in globals() and v == SPECIAL_BUBBLE2_INDEX:
                    return False
                if 'SPECIAL_BUBBLE3_INDEX' in globals() and v == SPECIAL_BUBBLE3_INDEX:
                    return False
                if 'BOMB_INDICES' in globals() and v in BOMB_INDICES:
                    return False
                if 'SNAKE_INDEX' in globals() and SNAKE_INDEX is not None and v == SNAKE_INDEX:
                    return False
                return True
            return False
        if a == SPECIAL_BUBBLE3_INDEX and is_normal(b):
            return True
        if b == SPECIAL_BUBBLE3_INDEX and is_normal(a):
            return True

    tmp = grid[r1][c1]
    grid[r1][c1] = grid[r2][c2]
    grid[r2][c2] = tmp
    ok = has_any_match(grid)
    grid[r2][c2] = grid[r1][c1]
    grid[r1][c1] = tmp
    return ok

def has_moves(grid):
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if c + 1 < GRID_COLS and would_match_after_swap(grid, r, c, r, c + 1):
                return True
            if r + 1 < GRID_ROWS and would_match_after_swap(grid, r, c, r + 1, c):
                return True
    return False

def score_for_chain(length):
    if length < 3:
        return 0
    if length >= 5:
        return 20 + (length - 3) * 20 
    return 15 + (length - 3) * 15


def draw_board(surface, grid, images, font, selection=None, highlight_groups=None, chain_sizes=None):
    pygame.draw.rect(surface, GRID_BG, (*BOARD_OFFSET, *BOARD_SIZE))
    for i in range(GRID_COLS + 1):
        x = BOARD_OFFSET[0] + i * CELL_SIZE
        pygame.draw.line(surface, GRID_LINE, (x, BOARD_OFFSET[1]), (x, BOARD_OFFSET[1] + BOARD_SIZE[1]))
    for j in range(GRID_ROWS + 1):
        y = BOARD_OFFSET[1] + j * CELL_SIZE
        pygame.draw.line(surface, GRID_LINE, (BOARD_OFFSET[0], y), (BOARD_OFFSET[0] + BOARD_SIZE[0], y))
    
    if highlight_groups:
        for idx, group in enumerate(highlight_groups):
            chain_len = chain_sizes[idx] if chain_sizes else len(group)

            if chain_len == 3:
                color = HL_COLOR_3
            elif chain_len == 4:
                color = HL_COLOR_4
            elif chain_len == 9:
                color = HL_BOMB
            elif chain_len == 17:
                color = HL_BOMB
            else:
                color = HL_COLOR_5PLUS

            for (r, c) in group:
                x, y = grid_to_px(r, c)
                rect = pygame.Rect(x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4)
                pygame.draw.rect(surface, color, rect, border_radius=12)

        for idx, group in enumerate(highlight_groups):
            rs = [r for (r, c) in group]
            cs = [c for (r, c) in group]
            minx, miny = grid_to_px(min(rs), min(cs))
            maxx, maxy = grid_to_px(max(rs), max(cs))
            center = (minx + (maxx - minx) + CELL_SIZE // 2, miny + (maxy - miny) + CELL_SIZE // 2)
            label = font.render(f"x{chain_sizes[idx]}", True, (30, 30, 30))
            rect = label.get_rect(center=center)
            surface.blit(label, rect)

    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            val = grid[r][c]
            if val is None:
                continue
            img = images[val]
            x, y = grid_to_px(r, c)
            surface.blit(img, (x, y))

    if selection is not None:
        r, c = selection
        x, y = grid_to_px(r, c)
        pygame.draw.rect(surface, (255, 255, 255), (x + 3, y + 3, CELL_SIZE - 6, CELL_SIZE - 6), 3, border_radius=10)
    draw_overlay(surface)

def draw_header(surface, font, score, highscore,skin, difficulty=None):
    if skin ==1:
        text = font.render(f"{score}", True, (200,200,255))
        hs_text = font.render(f"{highscore}", True, (200,200,255))
    else:
        text = font.render(f"{score}", True, SCORE_COLOR)
        hs_text = font.render(f"{highscore}", True, SCORE_COLOR)

    surface.blit(text, (BOARD_OFFSET[0]+40, BOARD_OFFSET[1] - 78))
    surface.blit(hs_text, (WINDOW_SIZE[0] - BOARD_OFFSET[0] - hs_text.get_width()-42, BOARD_OFFSET[1] - 78))

def draw_hurry(surface, font):
        global hurry_flash_timer, timer_sound
        if hurry_flash_timer == 0:
            hurry_flash_timer = 20
            if timer_sound:
                try:
                    timer_sound.play()
                except Exception as e:
                    print("Error playing timer sound:", e)
        if hurry_flash_timer <= 10:
            text = font.render("HURRY!", True, (255, 80, 80))
            rect = text.get_rect(center=(100, WINDOW_SIZE[1] - 20))
            surface.blit(text, rect)
            rect1 = text.get_rect(center=(900, WINDOW_SIZE[1] - 20))
            surface.blit(text, rect1)
            hurry_flash_timer -= 1
            
        else:
            hurry_flash_timer -= 1
        
def draw_game_over(surface, custom_font, custom_font1, score, highscore, title_type):
    
    overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))
    if title_type == 2: title = custom_font.render("No more moves", True, GAMEOVER_COLOR) 
    else:
        title = custom_font.render("Time Is Up", True, GAMEOVER_COLOR)
    sub = custom_font1.render("Press R to restart or ESC to quit", True, (230, 230, 240))
    score_t = custom_font1.render(f"Final Score: {score}  |  High Score: {highscore}", True, (230, 230, 240))
    rect = title.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2 - 40))
    rect2 = sub.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2 + 40))
    rect3 = score_t.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2 + 5))
    surface.blit(title, rect)
    surface.blit(score_t, rect3)
    surface.blit(sub, rect2)


def pos_to_cell(mx, my):
    if not (BOARD_OFFSET[0] <= mx < BOARD_OFFSET[0] + BOARD_SIZE[0] and BOARD_OFFSET[1] <= my < BOARD_OFFSET[1] + BOARD_SIZE[1]):
        return None
    c = (mx - BOARD_OFFSET[0]) // CELL_SIZE
    r = (my - BOARD_OFFSET[1]) // CELL_SIZE
    return int(r), int(c)

def are_adjacent(a, b):
    (r1, c1), (r2, c2) = a, b
    return (abs(r1 - r2) == 1 and c1 == c2) or (abs(c1 - c2) == 1 and r1 == r2)

def draw_overlay(screen):
    global skin, OVERLAY_CACHE
    overlay_img = OVERLAY_CACHE.get("board", {}).get(skin)
    if overlay_img:
        screen.blit(overlay_img, (0, 0))
        return
    overlay_path = OVERLAY_PATHS["board"][1 if skin == 1 else 2]
    overlay_img = load_scaled_overlay(overlay_path, screen.get_size())
    OVERLAY_CACHE.setdefault("board", {})[skin] = overlay_img
    if overlay_img:
        screen.blit(overlay_img, (0, 0))

def draw_overlaytop(screen):
    global skin, OVERLAY_CACHE
    overlay_img = OVERLAY_CACHE.get("top", {}).get(skin)
    if overlay_img:
        screen.blit(overlay_img, (0, 0))
        return
    overlay_path = OVERLAY_PATHS["top"][1 if skin == 1 else 2]
    overlay_img = load_scaled_overlay(overlay_path, screen.get_size())
    OVERLAY_CACHE.setdefault("top", {})[skin] = overlay_img
    if overlay_img:
        screen.blit(overlay_img, (0, 0))

def draw_overlaytmenu(screen):
    global skin, OVERLAY_CACHE
    overlay_img = OVERLAY_CACHE.get("menu", {}).get(skin)
    if overlay_img:
        screen.blit(overlay_img, (0, 0))
        return
    overlay_path = OVERLAY_PATHS["menu"][1 if skin == 1 else 2]
    overlay_img = load_scaled_overlay(overlay_path, screen.get_size())
    OVERLAY_CACHE.setdefault("menu", {})[skin] = overlay_img
    if overlay_img:
        screen.blit(overlay_img, (0, 0))

def draw_volume_control(surface, volume, font):
    global mute
    bar_width = 20
    bar_height = WINDOW_SIZE[1] // 3 -160
    bar_x = WINDOW_SIZE[0] - 35
    bar_y = WINDOW_SIZE[1] // 3 +95
    filled_height = int(bar_height * volume)
    bar_surface = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
    half_height = bar_height // 2
    quarter_height = half_height // 2

    bottom_rect = pygame.Rect(0, bar_height - half_height, bar_width, half_height)
    pygame.draw.rect(bar_surface, (50, 200, 100), bottom_rect)

    middle_rect = pygame.Rect(0, bar_height - half_height - quarter_height, bar_width, quarter_height)
    pygame.draw.rect(bar_surface, (255, 165, 50), middle_rect)

    top_rect = pygame.Rect(0, 0, bar_width, quarter_height)
    pygame.draw.rect(bar_surface, (255, 50, 50), top_rect)

    crop_rect = pygame.Rect(0, bar_height - filled_height, bar_width, filled_height)
    if not mute:surface.blit(bar_surface, (bar_x, bar_y + (bar_height - filled_height)), crop_rect)

    up_rect = pygame.Rect(bar_x - 10, bar_y - 50, bar_width + 20, 40)
    down_rect = pygame.Rect(bar_x - 10, bar_y + bar_height + 10, bar_width + 20, 40)
    pygame.draw.rect(surface, (200, 200, 240), up_rect, border_radius=18)
    pygame.draw.rect(surface, (200, 200, 240), down_rect, border_radius=18)

    up_label = font.render("+", True, (30, 30, 30))
    down_label = font.render("-", True, (30, 30, 30))
    surface.blit(up_label, up_label.get_rect(center=up_rect.center))
    surface.blit(down_label, down_label.get_rect(center=down_rect.center))
    return up_rect, down_rect

def draw_volume_control1(surface, m_volume, font):
    global mute
    bar_width = 20
    bar_height = WINDOW_SIZE[1] // 3 -160
    bar_x = 15
    bar_y = WINDOW_SIZE[1] // 3 +95
    filled_height = int(bar_height * m_volume)
    bar_surface = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
    half_height = bar_height // 2
    quarter_height = half_height // 2

    bottom_rect = pygame.Rect(0, bar_height - half_height, bar_width, half_height)
    pygame.draw.rect(bar_surface, (50, 200, 100), bottom_rect)
    middle_rect = pygame.Rect(0, bar_height - half_height - quarter_height, bar_width, quarter_height)
    pygame.draw.rect(bar_surface, (255, 165, 50), middle_rect)
    top_rect = pygame.Rect(0, 0, bar_width, quarter_height)
    pygame.draw.rect(bar_surface, (255, 50, 50), top_rect)

    crop_rect = pygame.Rect(0, bar_height - filled_height, bar_width, filled_height)
    if not mute:surface.blit(bar_surface, (bar_x, bar_y + (bar_height - filled_height)), crop_rect)

    up_rect1 = pygame.Rect(bar_x - 9, bar_y - 49, bar_width + 19, 39)
    down_rect1 = pygame.Rect(bar_x - 9, bar_y + bar_height + 9, bar_width + 19, 39)
    pygame.draw.rect(surface, (200, 200, 240), up_rect1, border_radius=18)
    pygame.draw.rect(surface, (200, 200, 240), down_rect1, border_radius=18)
    up_label = font.render("+", True, (30, 30, 30))
    down_label = font.render("-", True, (30, 30, 30))
    surface.blit(up_label, up_label.get_rect(center=up_rect1.center))
    surface.blit(down_label, down_label.get_rect(center=down_rect1.center))
    return up_rect1, down_rect1

def get_bomb_effect_cells(bomb_type, r, c):
    cells = set()
    if bomb_type == 0:
        for cc in range(GRID_COLS):
            cells.add((r, cc))
    elif bomb_type == 1:
        for rr in range(GRID_ROWS):
            cells.add((rr, c))
    else:
        for cc in range(GRID_COLS):
            cells.add((r, cc))
        for rr in range(GRID_ROWS):
            cells.add((rr, c))
    return cells

def insert_random_bomb_top(grid, bomb_indices):
    if not bomb_indices:
        return
    c = random.randrange(0, GRID_COLS)
    bomb_idx = random.choice(bomb_indices)
    for r in range(GRID_ROWS - 1, 0, -1):
        grid[r][c] = grid[r-1][c]
    grid[0][c] = bomb_idx

def generate_snake_path(start_r, start_c, steps=10):
    path = [(start_r, start_c)]
    for _ in range(steps - 1):
        r, c = path[-1]
        nbrs = []
        if r > 0: nbrs.append((r - 1, c))
        if r < GRID_ROWS - 1: nbrs.append((r + 1, c))
        if c > 0: nbrs.append((r, c - 1))
        if c < GRID_COLS - 1: nbrs.append((r, c + 1))
        random.shuffle(nbrs)
        if len(path) >= 2:
            prev = path[-2]
            if prev in nbrs:
                nbrs.remove(prev)
                nbrs.append(prev)
        if nbrs:
            path.append(nbrs[0])
        else:
            break
    return path

##################################################################
#     #####     ###   #######   ###   ### ###   ####        ######
#   #########   ###    #####    ###   ##   ##   ###   ####   #####
#  ##  ###  ##  ###     ###     ###   #     #   ###   ####   #####
# ###   #   ### ###      #      ###      #      ###   ############
#  ##  ###  ##  ###   #     #   ###     ###     ###   ####     ###
#   #### ####   ###   ##   ##   ###    #####    ###   ####   #####
#      ###      ###   ### ###   ###   #######   ####        ######
##################################################################

async def main():
    global BOMB_INDICES, mute, hurry_flash_timer, skin, timer_sound, SNAKE_INDEX
    pygame.init()
    has_audio = False
    if not IS_WEB:
        try:
            pygame.mixer.init() 
            has_audio = True
        except pygame.error as e:
            print("Audio disabled:", e)
    else:
        print("Running under web build, delaying audio init until user interaction")
    volume = 0.5
    m_volume = 0.5
    pop_sounds = []
    timer_sound = None
    timer_sound1 = None
    menu_button_sound = None
    bomb_sound = None
    snake_sound = None
    fiver_sound = None
    audio_assets_loaded = False

    def initialize_audio(force_music=False):
        nonlocal has_audio, audio_assets_loaded, pop_sounds, timer_sound1
        nonlocal menu_button_sound, bomb_sound, snake_sound, fiver_sound, m_volume
        global timer_sound
        if not has_audio:
            try:
                pygame.mixer.init()
                has_audio = True
            except pygame.error as e:
                print("Audio init failed:", e)
                return
        if not audio_assets_loaded:
            pygame.mixer.set_num_channels(16)
            try:
                pygame.mixer.music.load(os.path.join("jsounds", "music1.ogg"))
                pygame.mixer.music.set_volume(m_volume)
            except Exception as e:
                print("Music load failed:", e)
            pop_sounds = load_pop_sounds(audio_enabled=True)
            try:
                timer_sound = pygame.mixer.Sound(timer_sound_file)
            except Exception as e:
                print("Error loading timer sound:", e)
                timer_sound = None
            try:
                timer_sound1 = pygame.mixer.Sound(timer_sound_file1)
            except Exception as e:
                print("Error loading timer sound1:", e)
                timer_sound1 = None
            try:
                menu_button_sound = pygame.mixer.Sound(button_sound_file)
            except Exception as e:
                print("Error loading menu button sound:", e)
                menu_button_sound = None
            try:
                bomb_sound = pygame.mixer.Sound(BOMB_SOUND_FILE)
            except Exception as e:
                print("Error loading bomb sound:", e)
                bomb_sound = None
            try:
                snake_sound = pygame.mixer.Sound(snake_sound_file)
            except Exception as e:
                print("Error loading snake sound:", e)
                snake_sound = None
            try:
                fiver_sound = pygame.mixer.Sound(FIVER_SOUND_FILE)
            except Exception as e:
                print("Error loading fiver sound:", e)
                fiver_sound = None
            audio_assets_loaded = True
        if force_music and has_audio:
            try:
                pygame.mixer.music.play(-1)
            except Exception as e:
                print("Error starting music:", e)

    window_flags = pygame.RESIZABLE | pygame.DOUBLEBUF
    window = pygame.display.set_mode(WINDOW_SIZE, window_flags)
    screen = pygame.Surface(WINDOW_SIZE).convert_alpha()
    preload_overlays(WINDOW_SIZE)
    is_fullscreen = False
    windowed_size = WINDOW_SIZE
    icon_path = os.path.join("bubbles", "icon.png")
    try:
        icon_image = pygame.image.load(icon_path)
        pygame.display.set_icon(icon_image)
    except Exception as e:
        print("Icon load failed:", e)
    pygame.display.set_caption("Bot-Swapper")
    clock = pygame.time.Clock()

    font_small = pygame.font.Font(FONT_NAME, 28)
    font_medium = pygame.font.Font(FONT_NAME, 36)
    font_big = pygame.font.Font(FONT_NAME, 64)
    font_size = 64
    font_size1 = 30
    font_size2 = 48
    custom_font = load_font_safe(font_path, font_size, "custom_font")
    custom_font1 = load_font_safe(font_path, font_size1, "custom_font1")
    custom_font2 = load_font_safe(font_path, font_size2, "custom_font2")
    
    images, BOMB_INDICES = load_all_images()
    grid = create_grid(no_start_matches=True)
    score = 0
    highscores = load_highscores()
    highscore = 0

    selection = None
    showing_highlights_until = 0
    highlight_groups = None
    chain_sizes = None
    game_over = False
    title_type = 1
    game_state = MENU
    buttons = []
    current_difficulty = None
    timer_duration = None
    timer_start = None
    timer_color = (80,255,80)
    timer_switch = False

    if has_audio:
        initialize_audio()

    bombs_unlocked = False
    snake_unlocked = False
    next_bomb_time = 0
    highlight_from_bomb = False

    def to_logical(pos, win_size):
        wx, wy = win_size
        bw, bh = WINDOW_SIZE
        if wx == 0 or wy == 0:
            return pos
        scale = min(wx / bw, wy / bh)
        render_w = int(bw * scale)
        render_h = int(bh * scale)
        off_x = (wx - render_w) // 2
        off_y = (wy - render_h) // 2
        x, y = pos
        if x < off_x or y < off_y or x >= off_x + render_w or y >= off_y + render_h:
            return (-10000, -10000)
        lx = int((x - off_x) / scale)
        ly = int((y - off_y) / scale)
        return (lx, ly)

    snake_mode = False
    snake_queue = []
    score_messages = []

    def add_score_message(points):
        try:
            txt = f"+{points}"
            until = pygame.time.get_ticks() + 1200
            score_messages.append({"text": txt, "until": until})
        except Exception:
            pass
    running = True
    while running:
        dt = clock.tick(FPS)

        if has_audio:
            if not mute:
                pygame.mixer.music.set_volume(m_volume)
            else:
                pygame.mixer.music.set_volume(0.0)
                m_volume = 0.0
                volume = 0.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == KEYDOWN:
                if not audio_assets_loaded:
                    initialize_audio()
                if event.key == K_ESCAPE:
                    running = False
                if event.key == K_m:
                    mute = not mute
                if event.key == K_LEFT:
                    skin = 1
                if event.key == K_RIGHT:
                    skin = 2
                if event.key == K_F11 or (event.key == K_RETURN and (pygame.key.get_mods() & KMOD_ALT)):
                    if not is_fullscreen:
                        windowed_size = window.get_size()
                        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
                        is_fullscreen = True
                    else:
                        window = pygame.display.set_mode(windowed_size, window_flags)
                        is_fullscreen = False
                
                if event.key == K_r:
                    game_state = MENU
                    game_over = False
                    selection = None
                    highlight_groups = None
                    chain_sizes = None
                    showing_highlights_until = 0
                    score = 0
                    grid = create_grid(no_start_matches=True)
                    bombs_unlocked = False
            
            elif event.type == VIDEORESIZE and not is_fullscreen:
                windowed_size = (event.w, event.h)
                window = pygame.display.set_mode(windowed_size, window_flags)

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if not audio_assets_loaded:
                    initialize_audio()
                logical_pos = to_logical(event.pos, window.get_size())
                if game_state == MENU:
                    for rect, label in buttons:
                        if rect.collidepoint(logical_pos):
                            current_difficulty = label
                            timer_duration = DIFFICULTY_SETTINGS[label]
                            timer_start = pygame.time.get_ticks()
                            highscore = highscores.get(current_difficulty, 0)
                            current_difficulty = label
                            timer_duration = DIFFICULTY_SETTINGS[label]
                            timer_start = pygame.time.get_ticks()
                            grid = create_grid(no_start_matches=True)
                            score = 0
                            selection = None
                            showing_highlights_until = 0
                            highlight_groups = None
                            chain_sizes = None
                            game_over = False
                            game_state = PLAYING
                            if has_audio:
                                try:
                                    pygame.mixer.music.play(-1)
                                except Exception as e:
                                    print("Error starting music:", e)
                                if menu_button_sound:
                                    try:
                                        menu_button_sound.set_volume(volume)
                                        menu_button_sound.play()
                                    except Exception as e:
                                        print("Error playing menu button sound:", e)

                elif game_state == PLAYING and not game_over:
                    if event.type == MOUSEBUTTONDOWN and event.button == 1:
                        if game_state == PLAYING:
                            up_rect, down_rect = draw_volume_control(screen, volume, font_medium)
                            if up_rect.collidepoint(logical_pos):
                                volume = min(1.0, volume + 0.1)
                                mute = False
                            elif down_rect.collidepoint(logical_pos):
                                volume = max(0.0, volume - 0.1)
                            up_rect1, down_rect1 = draw_volume_control1(screen, m_volume, font_medium)
                            if up_rect1.collidepoint(logical_pos):
                                m_volume = min(1.0, m_volume + 0.1)
                                mute = False
                            elif down_rect1.collidepoint(logical_pos):
                                m_volume = max(0.0, m_volume - 0.1)
                    cell = pos_to_cell(*logical_pos)
                    if cell is None:
                        selection = None
                    else:
                        if selection is None:
                            selection = cell
                        else:
                            if cell == selection:
                                selection = None
                            elif are_adjacent(selection, cell):
                                (r1, c1), (r2, c2) = selection, cell
                                if not in_bounds(r1, c1) or not in_bounds(r2, c2):
                                    selection = None
                                    continue

                                a = grid[r1][c1]
                                b = grid[r2][c2]
                                a_is_bomb = a in BOMB_INDICES
                                b_is_bomb = b in BOMB_INDICES

                                if ((a == SPECIAL_BUBBLE_INDEX or b == SPECIAL_BUBBLE_INDEX) and not (a_is_bomb or b_is_bomb)):
                                    selection = None
                                else:
                                    grid[r1][c1], grid[r2][c2] = b, a
                                    a_is_b9 = ('SPECIAL_BUBBLE3_INDEX' in globals()) and (a == SPECIAL_BUBBLE3_INDEX)
                                    b_is_b9 = ('SPECIAL_BUBBLE3_INDEX' in globals()) and (b == SPECIAL_BUBBLE3_INDEX)
                                    if a_is_b9 or b_is_b9:
                                        total = len(BUBBLE_NAMES)
                                        def is_normal(v):
                                            if v is None:
                                                return False
                                            if isinstance(v, int) and 0 <= v < total:
                                                if v == SPECIAL_BUBBLE_INDEX:
                                                    return False
                                                if 'SPECIAL_BUBBLE2_INDEX' in globals() and v == SPECIAL_BUBBLE2_INDEX:
                                                    return False
                                                if 'SPECIAL_BUBBLE3_INDEX' in globals() and v == SPECIAL_BUBBLE3_INDEX:
                                                    return False
                                                if 'BOMB_INDICES' in globals() and v in BOMB_INDICES:
                                                    return False
                                                if 'SNAKE_INDEX' in globals() and SNAKE_INDEX is not None and v == SNAKE_INDEX:
                                                    return False
                                                return True
                                            return False

                                        dest_r_b9, dest_c_b9 = None, None
                                        if a_is_b9 and is_normal(b):
                                            target = b
                                            dest_r_b9, dest_c_b9 = r2, c2
                                        elif b_is_b9 and is_normal(a):
                                            target = a
                                            dest_r_b9, dest_c_b9 = r1, c1
                                        else:
                                            target = None
                                        if target is not None:
                                            affected = set()
                                            for rr in range(GRID_ROWS):
                                                for cc in range(GRID_COLS):
                                                    if grid[rr][cc] == target:
                                                        affected.add((rr, cc))
                                            if dest_r_b9 is not None:
                                                affected.add((dest_r_b9, dest_c_b9))
                                            if affected:
                                                highlight_groups = [affected]
                                                chain_sizes = [len(affected)]
                                                highlight_from_bomb = True
                                                added_points = score_for_chain(len(affected))
                                                score += added_points
                                                add_score_message(added_points)
                                                showing_highlights_until = pygame.time.get_ticks() + HIGHLIGHT_DELAY_MS
                                                selection = None
                                                continue

                                    if a_is_bomb or b_is_bomb:
                                        if a_is_bomb and not b_is_bomb:
                                            dest_r, dest_c = r2, c2
                                            power_idx = a
                                        elif b_is_bomb and not a_is_bomb:
                                            dest_r, dest_c = r1, c1
                                            power_idx = b
                                        else:
                                            dest_r, dest_c = r2, c2
                                            power_idx = b

                                        if SNAKE_INDEX is not None and power_idx == SNAKE_INDEX:
                                            if snake_sound:
                                                if not mute:
                                                    snake_sound.set_volume(volume)
                                                else:
                                                    snake_sound.set_volume(0.0)
                                                snake_sound.play()
                                            snake_queue = generate_snake_path(dest_r, dest_c, steps=10)
                                            if snake_queue:
                                                snake_mode = True
                                                highlight_groups = [set([snake_queue[0]])]
                                                chain_sizes = [1]
                                                highlight_from_bomb = True
                                                showing_highlights_until = pygame.time.get_ticks() + SNAKE_STEP_DELAY_MS
                                            selection = None
                                        else:
                                            if power_idx in BOMB_INDICES[:3]:
                                                bomb_type = BOMB_INDICES[:3].index(power_idx)
                                            else:
                                                bomb_type = random.randrange(0, 3)
                                            
                                            if bomb_sound:
                                                if not mute:
                                                    bomb_sound.set_volume(volume)
                                                else:
                                                    bomb_sound.set_volume(0.0)
                                                bomb_sound.play()
                                            affected = get_bomb_effect_cells(bomb_type, dest_r, dest_c)
                                            highlight_groups = [affected]
                                            chain_sizes = [len(affected)]
                                            highlight_from_bomb = True
                                            added_points = score_for_chain(len(affected))
                                            score += added_points
                                            add_score_message(added_points)
                                            next_bomb_time += 1
                                            if timer_duration:
                                                timer_start = add_time(1, timer_duration, timer_start)
                                            if pop_sounds:
                                                s = random.choice(pop_sounds)
                                                if not mute:
                                                    s.set_volume(volume)
                                                else:
                                                    s.set_volume(0.0)
                                                    volume = 0.0
                                                    m_volume = 0.0
                                                s.play()
                                            showing_highlights_until = pygame.time.get_ticks() + HIGHLIGHT_DELAY_MS
                                            selection = None

                                    else:
                                        matches = find_all_matches_wild_any(grid)
                                        if matches:
                                            selection = None
                                            highlight_groups = matches
                                            chain_sizes = [len(g) for g in matches]
                                            highlight_from_bomb = False
                                            added_points = sum(score_for_chain(len(g)) for g in matches)
                                            score += added_points
                                            add_score_message(added_points)

                                            if  any(size >= 5 for size in chain_sizes):
                                                if fiver_sound:
                                                    try:
                                                        if not mute:
                                                            fiver_sound.set_volume(volume)
                                                        else:
                                                            fiver_sound.set_volume(0.0)
                                                        fiver_sound.play()
                                                    except Exception as e:
                                                        print("Error playing fiver sound:", e)

                                            next_bomb_time +=1
                                            if timer_duration:
                                                timer_start = add_time(1, timer_duration, timer_start)
                                            if pop_sounds:
                                                s = random.choice(pop_sounds)
                                                s.set_volume(volume)
                                                s.play()
                                            showing_highlights_until = pygame.time.get_ticks() + HIGHLIGHT_DELAY_MS
                                        else:
                                            grid[r1][c1], grid[r2][c2] = a, b
                                            selection = cell
                            else:
                                selection = cell

        now = pygame.time.get_ticks()
        if not bombs_unlocked and score >= 1500:
            bombs_unlocked = True
            next_bomb_time = 0

        if bombs_unlocked and next_bomb_time >= 40:
            insert_random_bomb_top(grid, BOMB_INDICES)
            next_bomb_time = 0

        if not snake_unlocked and score >= 3000:
            snake_unlocked = True
            if SNAKE_INDEX is not None and SNAKE_INDEX not in BOMB_INDICES:
                BOMB_INDICES.append(SNAKE_INDEX)

        if highlight_groups and now >= showing_highlights_until and not game_over:
            if snake_mode:
                if snake_queue:
                    r, c = snake_queue.pop(0)
                    if in_bounds(r, c):
                        grid[r][c] = None
                if snake_queue:
                    highlight_groups = [set([snake_queue[0]])]
                    chain_sizes = [1]
                    highlight_from_bomb = True
                    showing_highlights_until = pygame.time.get_ticks() + SNAKE_STEP_DELAY_MS
                else:
                    highlight_groups = None
                    chain_sizes = None
                    highlight_from_bomb = False
                    snake_mode = False
                    apply_gravity_and_refill(grid, score)
                    cascade_matches = find_all_matches_wild_any(grid)
                    if cascade_matches:
                        highlight_groups = cascade_matches
                        chain_sizes = [len(g) for g in cascade_matches]
                        highlight_from_bomb = False
                        added_points = sum(score_for_chain(len(g)) for g in cascade_matches)
                        score += added_points
                        add_score_message(added_points)
                        if any(size >= 5 for size in chain_sizes):
                            if fiver_sound:
                                try:
                                    if not mute:
                                        fiver_sound.set_volume(volume)
                                    else:
                                        fiver_sound.set_volume(0.0)
                                    fiver_sound.play()
                                except Exception as e:
                                    print("Error playing fiver sound:", e)
                        next_bomb_time += 1
                        if timer_duration:
                            timer_start = add_time(1, timer_duration, timer_start)
                        if pop_sounds:
                            s = random.choice(pop_sounds)
                            if not mute:
                                s.set_volume(volume)
                                if has_audio:
                                    try:
                                        pygame.mixer.music.set_volume(m_volume)
                                    except Exception as e:
                                        print("Error setting music volume:", e)
                            else:
                                s.set_volume(0.0)
                                volume = 0.0
                                m_volume = 0.0
                            s.play()
                        showing_highlights_until = pygame.time.get_ticks() + HIGHLIGHT_DELAY_MS
                    else:
                        if not has_moves(grid):
                            title_type = 2
                            game_over = True
                            game_state = GAME_OVER
                            save_highscore(current_difficulty, score)
                            highscores = load_highscores()
                            highscore = highscores.get(current_difficulty, 0)
            else:
                for group in highlight_groups:
                    for (r, c) in group:
                        if highlight_from_bomb:
                            grid[r][c] = None
                        else:
                            if grid[r][c] != SPECIAL_BUBBLE_INDEX:
                                grid[r][c] = None

                highlight_groups = None
                chain_sizes = None
                highlight_from_bomb = False
                apply_gravity_and_refill(grid, score)
                cascade_matches = find_all_matches_wild_any(grid)
                if cascade_matches:
                    highlight_groups = cascade_matches
                    chain_sizes = [len(g) for g in cascade_matches]
                    highlight_from_bomb = False
                    added_points = sum(score_for_chain(len(g)) for g in cascade_matches)
                    score += added_points
                    add_score_message(added_points)

                    if  any(size >= 5 for size in chain_sizes):
                        if fiver_sound:
                            try:
                                if not mute:
                                    fiver_sound.set_volume(volume)
                                else:
                                    fiver_sound.set_volume(0.0)
                                fiver_sound.play()
                            except Exception as e:
                                print("Error playing fiver sound:", e)

                    next_bomb_time += 1
                    if timer_duration:
                        timer_start = add_time(1, timer_duration, timer_start)
                    if pop_sounds:
                        s = random.choice(pop_sounds)
                        if not mute:
                            s.set_volume(volume)
                            if has_audio:
                                try:
                                    pygame.mixer.music.set_volume(m_volume)
                                except Exception as e:
                                    print("Error setting music volume:", e)
                        else:
                            s.set_volume(0.0)
                            volume = 0.0
                            m_volume = 0.0
                        s.play()

                    showing_highlights_until = pygame.time.get_ticks() + HIGHLIGHT_DELAY_MS
                else:
                    if not has_moves(grid):
                        title_type = 2
                        game_over = True
                        game_state = GAME_OVER
                        save_highscore(current_difficulty, score)
                        highscores = load_highscores()
                        highscore = highscores.get(current_difficulty, 0)

        if game_state == PLAYING and not game_over:
            elapsed = (pygame.time.get_ticks() - timer_start) // 1000 if timer_duration else 0
            if timer_duration and elapsed >= timer_duration:
                title_type = 1
                game_over = True
                game_state = GAME_OVER
                save_highscore(current_difficulty, score)
                highscores = load_highscores()
                highscore = highscores.get(current_difficulty, 0)
                bombs_unlocked = False
                next_bomb_time = 0
                highlight_from_bomb = False

        screen.fill(BG_COLOR)

        if game_state == MENU:
            buttons = draw_menu(screen, custom_font2, custom_font1, skin)

        elif game_state == PLAYING:
            draw_board(screen, grid, images, font_small, selection, highlight_groups, chain_sizes)
            draw_header(screen, custom_font1, score, highscores.get(current_difficulty, 0),skin, current_difficulty)
            elapsed = (pygame.time.get_ticks() - timer_start) // 1000 if timer_duration else 0
            if timer_duration and (timer_duration - elapsed) >= 23 and timer_duration and (timer_duration - elapsed) <= 24:
                timer_switch = True

            elif timer_duration and (timer_duration - elapsed) >= 21 and timer_duration and (timer_duration - elapsed) < 22:
                if timer_sound1:
                    try:
                        timer_sound1.set_volume(volume)
                        if timer_switch:
                            timer_sound1.play()
                            timer_switch = False
                    except Exception as e:
                        print("Error playing timer_sound1:", e)
            elif timer_duration and (timer_duration - elapsed) >= 11 and timer_duration and (timer_duration - elapsed) <= 20:
                timer_color = (200,160,80)

            elif timer_duration and (timer_duration - elapsed) <= 10:
                draw_hurry(screen, custom_font1)
                timer_color = (200,80,80)
                if timer_sound:
                    try:
                        timer_sound.set_volume(volume)
                    except Exception as e:
                        print("Error setting timer_sound volume:", e)
            else:
                timer_color = (80,200,80)
            draw_timer(screen, elapsed, timer_duration, timer_color)    
            up_rect, down_rect = draw_volume_control(screen, volume, font_medium)
            up_rect1, down_rect1 = draw_volume_control1(screen, m_volume, font_medium)
            draw_overlaytop(screen)

        elif game_state == GAME_OVER:
            draw_board(screen, grid, images, font_small, selection, highlight_groups, chain_sizes)            
            draw_header(screen, custom_font1, score, highscores.get(current_difficulty, 0),skin, current_difficulty)
            draw_overlaytop(screen)
            draw_game_over(screen, custom_font, custom_font1, score, highscore, title_type)

        now = pygame.time.get_ticks()
        score_messages[:] = [m for m in score_messages if m.get("until", 0) > now]
        base_y = WINDOW_SIZE[1] - 20
        for idx, m in enumerate(reversed(score_messages[-3:])):
            txt = m.get("text")
            if not txt:
                continue
            if skin == 1:
                col = (200, 200, 255)
            else:
                col = SCORE_COLOR
            surf = custom_font1.render(txt, True, col)
            rect = surf.get_rect(center=(WINDOW_SIZE[0]//2, base_y - idx*28))
            screen.blit(surf, rect)

        win_w, win_h = window.get_size()
        base_w, base_h = WINDOW_SIZE
        scale = min(win_w / base_w, win_h / base_h) if win_w and win_h else 1.0
        render_w = int(base_w * scale)
        render_h = int(base_h * scale)
        off_x = (win_w - render_w) // 2
        off_y = (win_h - render_h) // 2

        window.fill((0, 0, 0))

        if render_w != base_w or render_h != base_h:
            scaled = pygame.transform.smoothscale(screen, (render_w, render_h))
            window.blit(scaled, (off_x, off_y))
        else:
            window.blit(screen, (off_x, off_y))
        pygame.display.flip()

        # Yield control so pygbag's async scheduler can service other tasks.
        await asyncio.sleep(0)

    pygame.quit()
if __name__ == "__main__":
    asyncio.run(main())
