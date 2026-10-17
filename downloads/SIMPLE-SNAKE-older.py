import random
import textwrap
import turtle

CREDITS = [
    "Dylan Rhodez, coded with the following resources > Claude Ai, "
    "w3schools.com, docs.python-guide.org",
    "Thank you for visiting my site, and thank you for playing!",
]

STEP = 20
BOUND = 280          # left/right/bottom limit for the snake's head
TOP_BOUND = 220      # top limit: the strip above it is the HUD wall area
SPAWN_X = range(-BOUND, BOUND + STEP, STEP)        # every column the head can reach
SPAWN_Y = range(-BOUND, TOP_BOUND + STEP, STEP)    # every row the head can reach
TOP_SPEED = 10           # boosted speed (speed + boost) can never exceed this
MIN_SPEED = 1
MIN_BOOST = 1
OVERRIDE_MAX = 20        # speed and boost caps while the speed limit override is on

DEFAULT_SPEED = 6
DEFAULT_BOOST = 2
speed_level = DEFAULT_SPEED    # 1 (slow) .. 9
boost_level = DEFAULT_BOOST    # extra speed points while holding the arrow key
state = "menu"           # "menu", "options", "credits", "dev", "playing"
paused = False
game_id = 0              # identifies the current game so stale timers stop
title_clicks = 0         # clicks on the title; 20 unlocks dev settings
dev_unlocked = False
show_hitboxes = False
speed_override = False   # dev option: ignore the speed + boost <= 10 limit
show_spots = False       # dev option: show every possible food spawn position
spot_items = []
menu_msg = None
hb_items = []            # canvas items for the hitbox overlay
pause_items = []         # canvas items for the pause window

# Hitbox colors = 50% yellow blended with what's underneath
HB_HEAD = "#7fff00"      # over lime head
HB_BODY = "#7fbf00"      # over green body
HB_FOOD = "#7f7f00"      # over black background
HB_FOOD_DOT = "#ff7f00"  # over red food
HB_WALL = "#7fdf7f"      # over blue wall
score = 0
high = 0
buttons = []             # (x1, y1, x2, y2, callback)
segments = []
held = set()             # directions whose arrow key is currently held


def max_speed():
    return OVERRIDE_MAX if speed_override else TOP_SPEED - 1


def max_boost():
    return OVERRIDE_MAX if speed_override else TOP_SPEED - speed_level


def apply_limits():
    """Clamp speed and boost to whatever limits are currently active."""
    global speed_level, boost_level
    speed_level = max(MIN_SPEED, min(max_speed(), speed_level))
    boost_level = max(MIN_BOOST, min(max_boost(), boost_level))


def delay_ms():
    level = speed_level + (boost_level if head.direction in held else 0)
    if level <= TOP_SPEED:
        return int((0.20 - 0.015 * level) * 1000)   # 185 ms (1) .. 50 ms (10)
    return max(1, int(50 * 0.8 ** (level - TOP_SPEED)))  # keeps getting faster past 10


# ---------- Setup ----------
screen = turtle.Screen()
screen.title("SIMPLE SNAKE")
screen.bgcolor("black")
screen.setup(600, 600)
screen.tracer(0)
canvas = screen.getcanvas()

# Walls
border = turtle.Turtle()
border.hideturtle()
border.speed(0)
border.color("deep sky blue")
border.pensize(6)
border.penup()


def draw_border():
    border.clear()
    border.penup()
    border.goto(-BOUND - 10, -BOUND - 10)
    border.pendown()
    for _ in range(4):
        border.forward(2 * BOUND + 20)
        border.left(90)
    border.penup()
    # Divider wall: separates the HUD (score + pause) from the play area
    border.goto(-BOUND - 10, TOP_BOUND + 10)
    border.pendown()
    border.goto(BOUND + 10, TOP_BOUND + 10)
    border.penup()

# UI pen (menus + buttons)
ui = turtle.Turtle()
ui.hideturtle()
ui.speed(0)
ui.penup()

# Game objects
head = turtle.Turtle("square")
head.color("lime")
head.penup()
head.hideturtle()
head.direction = "stop"

food = turtle.Turtle("circle")
food.color("red")
food.penup()
food.hideturtle()

score_pen = turtle.Turtle()
score_pen.hideturtle()
score_pen.penup()
score_pen.color("white")
score_pen.goto(-80, 250)


# ---------- UI helpers ----------
def text(msg, x, y, size=18, color="white", style="bold"):
    ui.color(color)
    ui.goto(x, y)
    ui.write(msg, align="center", font=("Courier", size, style))


def button(label, cx, cy, callback, w=200, h=50):
    x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    ui.color("white", "#1e3a5f")
    ui.pensize(3)
    ui.goto(x1, y1)
    ui.pendown()
    ui.begin_fill()
    for dx, dy in ((x2, y1), (x2, y2), (x1, y2), (x1, y1)):
        ui.goto(dx, dy)
    ui.end_fill()
    ui.penup()
    text(label, cx, cy - 12, 18)
    buttons.append((x1, y1, x2, y2, callback, label))


click_lock = False


def flash_button(x1, y1, x2, y2, label, callback):
    """Show a brighter 'pressed' version of the button for a moment, then run it."""
    global click_lock
    if click_lock:
        return
    click_lock = True
    items = [
        canvas.create_rectangle(x1, -y2, x2, -y1, fill="#4a90e2",
                                outline="yellow", width=3),
        canvas.create_text((x1 + x2) / 2, -(y1 + y2) / 2, text=label,
                           fill="white", font=("Courier", 18, "bold")),
    ]

    def finish():
        global click_lock
        for item in items:
            canvas.delete(item)
        click_lock = False
        callback()

    screen.ontimer(finish, 100)


def on_click(x, y):
    for x1, y1, x2, y2, cb, label in list(buttons):
        if x1 <= x <= x2 and y1 <= y <= y2:
            if label is None:
                cb()                       # invisible hit area (title)
            else:
                flash_button(x1, y1, x2, y2, label, cb)
            break


def draw_score():
    score_pen.clear()
    score_pen.write(f"Score: {score}  High: {high}", align="center",
                    font=("Courier", 18, "normal"))


# ---------- Screens ----------
def show_menu(message=None):
    global state, menu_msg
    state = "menu"
    menu_msg = message
    ui.clear()
    buttons.clear()
    score_pen.clear()
    text("SIMPLE SNAKE", 0, 150, 34, "lime")
    buttons.append((-170, 140, 170, 200, title_click, None))   # invisible title hit area
    if message:
        text(message, 0, 100, 16, "yellow")
    button("START", 0, 30, start_game)
    button("SETTINGS", 0, -50, show_options)
    button("CREDITS", 0, -130, show_credits)
    if dev_unlocked:
        button("DEV SETTINGS", 0, -210, show_dev_settings)
    elif title_clicks >= 10:
        text(f"{20 - title_clicks} clicks until dev settings", 0, -222, 16, "yellow")
    screen.update()


def title_click():
    global title_clicks, dev_unlocked
    if dev_unlocked:
        return
    title_clicks += 1
    if title_clicks >= 20:
        dev_unlocked = True
        show_menu("Developer settings unlocked!")
    else:
        show_menu(menu_msg)


def show_dev_settings():
    global state
    state = "dev"
    ui.clear()
    buttons.clear()
    text("DEV SETTINGS", 0, 190, 28, "lime")
    button(f"HITBOXES: {'ON' if show_hitboxes else 'OFF'}", 0, 60,
           toggle_hitboxes, w=280)
    button(f"FOOD SPOTS: {'ON' if show_spots else 'OFF'}", 0, -10,
           toggle_spots, w=280)
    button(f"SPEED OVERRIDE: {'ON' if speed_override else 'OFF'}", 0, -80,
           toggle_override, w=320)
    button("BACK", 0, -180, show_menu)
    screen.update()


def toggle_override():
    global speed_override
    speed_override = not speed_override
    apply_limits()          # turning it off pulls speed/boost back under 10
    show_dev_settings()


def toggle_spots():
    global show_spots
    show_spots = not show_spots
    show_dev_settings()


def clear_spots():
    for item in spot_items:
        canvas.delete(item)
    spot_items.clear()


def draw_spots():
    clear_spots()
    if not show_spots:
        return
    # Same positions the food spawner uses
    for x in SPAWN_X:
        for y in SPAWN_Y:
            item = canvas.create_oval(x - 2, -y - 2, x + 2, -y + 2,
                                      fill="cyan", outline="")
            canvas.tag_lower(item)     # keep dots underneath the snake
            spot_items.append(item)


def toggle_hitboxes():
    global show_hitboxes
    show_hitboxes = not show_hitboxes
    show_dev_settings()


def clear_hitboxes():
    for item in hb_items:
        canvas.delete(item)
    hb_items.clear()


def hb_rect(x1, y1, x2, y2, color):
    # turtle coords (y up) -> canvas coords (y down)
    hb_items.append(canvas.create_rectangle(x1, -y2, x2, -y1, fill=color, outline=""))


def draw_hitboxes():
    clear_hitboxes()
    if not show_hitboxes:
        return
    # Walls (the 6px border lines and the HUD divider)
    e, i, d = BOUND + 13, BOUND + 7, TOP_BOUND + 10
    hb_rect(-e, -e, -i, e, HB_WALL)
    hb_rect(i, -e, e, e, HB_WALL)
    hb_rect(-e, -e, e, -i, HB_WALL)
    hb_rect(-e, i, e, e, HB_WALL)
    hb_rect(-e, d - 3, e, d + 3, HB_WALL)
    # Body, head, food: collisions only happen on the same 20x20 grid cell
    for sg in segments:
        x, y = sg.xcor(), sg.ycor()
        hb_rect(x - 10, y - 10, x + 10, y + 10, HB_BODY)
    x, y = head.xcor(), head.ycor()
    hb_rect(x - 10, y - 10, x + 10, y + 10, HB_HEAD)
    x, y = food.xcor(), food.ycor()
    hb_rect(x - 10, y - 10, x + 10, y + 10, HB_FOOD)
    hb_items.append(canvas.create_oval(x - 10, -y - 10, x + 10, -y + 10,
                                       fill=HB_FOOD_DOT, outline=""))


def show_options():
    global state
    state = "options"
    ui.clear()
    buttons.clear()
    text("SETTINGS", 0, 190, 32, "lime")
    text(f"Speed: {speed_level}/{max_speed()}", 0, 120, 22)
    button("-  Slower", -90, 70, lambda: change_speed(-1), w=160)
    button("Faster  +", 90, 70, lambda: change_speed(1), w=160)
    text(f"Boost: +{boost_level} (max +{max_boost()})", 0, 0, 22)
    button("-  Less", -90, -50, lambda: change_boost(-1), w=160)
    button("More  +", 90, -50, lambda: change_boost(1), w=160)
    button("RESET DEFAULTS", 0, -115, reset_defaults, w=240)
    button("BACK", 0, -180, show_menu)
    screen.update()


def show_credits():
    global state
    state = "credits"
    ui.clear()
    buttons.clear()
    text("CREDITS", 0, 190, 32, "lime")
    y = 130
    for paragraph in CREDITS:
        for line in textwrap.wrap(paragraph, 40):
            text(line, 0, y, 14, "white", "normal")
            y -= 24
        y -= 14
    button("BACK", 0, -180, show_menu)
    screen.update()


def change_speed(d):
    global speed_level
    speed_level += d
    apply_limits()
    show_options()


def reset_defaults():
    global speed_level, boost_level
    speed_level = DEFAULT_SPEED
    boost_level = DEFAULT_BOOST
    show_options()


def change_boost(d):
    global boost_level
    boost_level += d
    apply_limits()
    show_options()


# ---------- Game ----------
def go(d, opposite):
    if state == "playing" and not paused and head.direction != opposite:
        head.direction = d


def press(d, opposite):
    held.add(d)
    go(d, opposite)


def release(d):
    held.discard(d)


# Space: press once to pause, press again (while paused) to quit to the menu.
space_down = False
space_gen = 0


def space_press():
    global space_down, space_gen
    space_gen += 1              # cancels a pending release (Linux key auto-repeat)
    if space_down:              # ignore auto-repeat while the key is held
        return
    space_down = True
    if state != "playing":
        return
    if paused:
        quit_to_menu()
    else:
        toggle_pause()


def space_release():
    gen = space_gen

    def clear():
        global space_down
        if gen == space_gen:
            space_down = False
    screen.ontimer(clear, 40)


# Movement: arrow keys and WASD
KEYS = {"up": ("Up", "w", "W"), "down": ("Down", "s", "S"),
        "left": ("Left", "a", "A"), "right": ("Right", "d", "D")}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}

screen.listen()
for direction, keys in KEYS.items():
    for key in keys:
        screen.onkeypress(lambda d=direction: press(d, OPPOSITE[d]), key)
        screen.onkeyrelease(lambda d=direction: release(d), key)
screen.onkeypress(space_press, "space")
screen.onkeyrelease(space_release, "space")
screen.onclick(on_click)


def move():
    x, y = head.xcor(), head.ycor()
    if head.direction == "up":
        head.sety(y + STEP)
    elif head.direction == "down":
        head.sety(y - STEP)
    elif head.direction == "left":
        head.setx(x - STEP)
    elif head.direction == "right":
        head.setx(x + STEP)


def clear_pause_window():
    for item in pause_items:
        canvas.delete(item)
    pause_items.clear()


def canvas_button(label, cx, cy, callback, w=220, h=50):
    x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    pause_items.append(canvas.create_rectangle(x1, -y2, x2, -y1, fill="#1e3a5f",
                                               outline="white", width=3))
    pause_items.append(canvas.create_text(cx, -cy, text=label, fill="white",
                                          font=("Courier", 18, "bold")))
    buttons.append((x1, y1, x2, y2, callback, label))


def draw_pause_window():
    # Small window in the middle of the play area. Built from canvas items
    # created after the last screen.update(), so it sits above the snake.
    pause_items.append(canvas.create_rectangle(-150, -100, 150, 120,
                                               fill="#0d1b2a", outline="yellow",
                                               width=4))
    pause_items.append(canvas.create_text(0, -65, text="PAUSED", fill="yellow",
                                          font=("Courier", 28, "bold")))
    canvas_button("QUIT TO MENU", 0, 5, quit_to_menu)
    canvas_button("RESUME", 0, -65, toggle_pause)
    pause_items.append(canvas.create_text(0, 105, text="SPACE again = quit to menu",
                                          fill="gray", font=("Courier", 10)))


def draw_hud_button():
    ui.clear()
    buttons.clear()
    clear_pause_window()
    if not paused:
        button("PAUSE", 215, 260, toggle_pause, w=110, h=36)
        screen.update()
    else:
        screen.update()          # raises the snake first; the window goes on top
        draw_pause_window()
        canvas.update()


def toggle_pause():
    global paused
    if state != "playing":
        return
    paused = not paused
    draw_hud_button()


def start_game():
    global state, score, paused, game_id
    state = "playing"
    paused = False
    game_id += 1
    draw_hud_button()
    draw_spots()
    score = 0
    held.clear()
    head.goto(0, 0)
    head.direction = "stop"
    head.showturtle()
    food.goto(0, 100)
    food.showturtle()
    draw_score()
    game_loop(game_id)


def quit_to_menu():
    if state == "playing" and paused:
        end_game(game_over=False)


def end_game(game_over=True):
    global paused
    paused = False
    clear_pause_window()
    clear_hitboxes()
    clear_spots()
    head.hideturtle()
    food.hideturtle()
    for s in segments:
        s.hideturtle()
    segments.clear()
    show_menu(f"Game over! Score: {score}" if game_over else None)


def game_loop(gid):
    global score, high
    if gid != game_id or state != "playing":
        return                          # stale timer from an earlier game
    if paused:
        screen.ontimer(lambda: game_loop(gid), 50)   # poll until resumed
        return

    # Wall collision
    if (abs(head.xcor()) > BOUND or head.ycor() > TOP_BOUND
            or head.ycor() < -BOUND):
        end_game()
        return

    # Eat food
    if head.distance(food) < 20:
        food.goto(random.choice(SPAWN_X), random.choice(SPAWN_Y))
        seg = turtle.Turtle("square")
        seg.color("green")
        seg.penup()
        segments.append(seg)
        score += 10
        high = max(high, score)
        draw_score()

    # Body follows head
    for i in range(len(segments) - 1, 0, -1):
        segments[i].goto(segments[i - 1].xcor(), segments[i - 1].ycor())
    if segments:
        segments[0].goto(head.xcor(), head.ycor())

    move()

    # Self collision
    if any(s.distance(head) < 20 for s in segments):
        end_game()
        return

    draw_hitboxes()
    screen.update()
    screen.ontimer(lambda: game_loop(gid), delay_ms())


# ---------- Fake terminal (shown before the game starts) ----------
TERM_FONT = ("Courier", 14, "normal")
term_lines = []          # (text, color)
term_input = ""
term_busy = False        # True while the "starting" message is showing


def term_print(msg, color="lime"):
    term_lines.append((msg, color))
    del term_lines[:-18]             # keep the newest lines so they fit on screen


def draw_terminal():
    ui.clear()
    y = 250
    for msg, color in term_lines:
        ui.color(color)
        ui.goto(-270, y)
        ui.write(msg, font=TERM_FONT)
        y -= 24
    if not term_busy:
        ui.color("lime")
        ui.goto(-270, y)
        ui.write("> " + term_input + "_", font=TERM_FONT)
    screen.update()


def show_terminal():
    global state
    state = "terminal"
    ui.clear()
    buttons.clear()
    score_pen.clear()
    term_lines.clear()
    term_print("SIMPLE SNAKE TERMINAL")
    term_print("")
    draw_terminal()


def launch_game():
    global term_busy
    term_busy = False
    ui.clear()
    draw_border()
    show_menu()


def term_submit():
    global term_input, term_busy
    cmd, term_input = term_input, ""
    term_print("> " + cmd, "white")
    word = cmd.strip().lower().rstrip("!. ")     # ignore case, spaces, trailing !/.
    if not word:
        return
    if word == "run":
        term_print("Starting SIMPLE SNAKE...")
        term_busy = True
        screen.ontimer(launch_game, 600)
    elif word == "help":
        term_print("Type RUN to run the game!")
    else:
        term_print("ERROR! Type 'help' to show help.", "red")


def on_terminal_key(event):
    global term_input
    if state != "terminal" or term_busy:
        return
    if event.keysym in ("Return", "KP_Enter"):
        term_submit()
    elif event.keysym == "BackSpace":
        term_input = term_input[:-1]
    elif len(event.char) == 1 and event.char.isprintable() and len(term_input) < 40:
        term_input += event.char
    draw_terminal()


# Bound on the window itself so it also sees W/A/S/D/space, which have their own
# game bindings on the canvas.
canvas.winfo_toplevel().bind("<Key>", on_terminal_key, add="+")

show_terminal()
screen.mainloop()
