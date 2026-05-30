import math
import ui
import sound
import speech
import random
import dialogs

# ====================== OUTLINED CHAR VIEW ======================

class OutlinedCharView(ui.View):
    def __init__(self, char, font_name='Helvetica-Bold',
                 font_size=150, fill_color=None,
                 outline_color='darkgray'):

        self.char = char
        self.font_name = font_name
        self.font_size = font_size
        self.touch_enabled = False

        self.text_width, self.text_height = ui.measure_string(char, font=(font_name, font_size))

        thick = 4
        padding = thick * 2 + 10
        super().__init__(frame=(0, 0, self.text_width + padding, self.text_height + padding))

        shifts = [(thick,0), (-thick,0), (0,thick), (0,-thick),
                  (thick,thick), (thick,-thick), (-thick,thick), (-thick,-thick)]

        self.outline_labels = []
        for dx, dy in shifts:
            lbl = ui.Label(frame=(thick + dx, thick + dy, self.text_width, self.text_height))
            lbl.text = char
            lbl.font = (font_name, font_size)
            lbl.text_color = outline_color
            lbl.alignment = ui.ALIGN_CENTER
            self.add_subview(lbl)
            self.outline_labels.append(lbl)

        self.fill = None
        if fill_color:
            self.set_fill_color(fill_color)
        else:
            self.set_fill_color('white')

    def set_fill_color(self, color):
        thick = 4

        if not self.fill:
            self.fill = ui.Label(frame=(thick, thick, self.text_width, self.text_height))
            self.fill.text = self.char
            self.fill.font = (self.font_name, self.font_size)
            self.fill.alignment = ui.ALIGN_CENTER
            self.add_subview(self.fill)

        self.fill.text_color = color if color else 'white'


# ====================== MODEL ======================

class Shape:
    def __init__(self, id, x, y, color):
        self.id = id
        self.x = x
        self.y = y
        self.color = color
        self.locked = False
        self.view = None


class Target:
    def __init__(self, id):
        self.id = id
        self.x = 0
        self.y = 0
        self.view = None


class GameModel:
    def __init__(self):
        self.mode = 'upper'
        self.shapes = []
        self.targets = []
        self.upper_alphabet = [chr(i) for i in range(65, 91)]
        self.lower_alphabet = [chr(i) for i in range(97, 123)]
        self.numbers_alphabet = [str(i) for i in range(10)]
        self.shape_types = ['circle', 'square', 'triangle', 'star', 'cross']
        self.alphabet = self.upper_alphabet
        self.start_index = 0

        self.words = ["father", "mother", "baby", "cat", "dog", "fish", "bird", "lizard",
                      "red", "orange", "yellow", "green", "blue", "purple", "Jasper"]
        self.current_word = ""

    def current_group(self):
        if self.mode == 'shapes':
            return self.shape_types
        elif self.mode == 'words':
            return list(self.current_word) if self.current_word else []
        else:
            return self.alphabet[self.start_index:self.start_index + 5]

    def init_targets(self):
        if self.mode == 'shapes':
            types = list(self.shape_types)
            random.shuffle(types)
            self.targets = [Target(t) for t in types]
        elif self.mode == 'words':
            if not self.current_word:
                self.pick_word()
            self.targets = [Target(c) for c in self.current_word]
        else:
            self.targets = [Target(c) for c in self.current_group()]

    def pick_word(self):
        if not self.words:
            self.words = ["cat", "dog", "fish"]
        self.current_word = random.choice(self.words)

    def next_group(self):
        if self.mode == 'shapes':
            pass
        elif self.mode == 'words':
            self.pick_word()
        else:
            self.start_index += 5
            if self.start_index >= len(self.alphabet):
                self.start_index = 0

    def is_completed(self):
        return (
            len(self.shapes) == len(self.targets) and
            all(s.locked for s in self.shapes)
        )


# ====================== VIEW ======================

class GameView(ui.View):

    def __init__(self):
        super().__init__()

        self.UI_HEIGHT = 180
        self.background_color = '#f0f0f0'
        self.play_bg_color = '#f0f0f0'

        self.current_color = '#E93F3F'
        self.letter_size = 150
        self.shape_size = 120
        self.mode = 'upper'
        self.snap_distance = self.letter_size * 0.8

        self.model = GameModel()
        self.model.mode = self.mode
        self.model.init_targets()

        self.dragging_shape = None
        self.drag_offset = (0, 0)
        self.last_hover_target = None

        self.color_map = {
            "Red": '#E93F3F',
            "Orange": '#FA8832',
            "Yellow": '#F6DE33',
            "Green": '#9FDE37',
            "Blue": '#194285',
            "Purple": '#7574D1'
        }

        self.color_buttons = []
        self.item_buttons = []

        self._create_ui()
        self.present('fullscreen')


    def layout(self):
        sw = self.width
        self.title_label.frame = (0, 5, sw, 40)

        for i, btn in enumerate(self.color_buttons):
            btn.frame = (5 + i * (sw / len(self.color_buttons)), 50,
                         (sw / len(self.color_buttons)) - 10, 40)

        for i, btn in enumerate(self.item_buttons):
            btn.frame = (5 + i * (sw / len(self.item_buttons)), 120,
                         (sw / len(self.item_buttons)) - 10, 40)

        self._position_targets()
        self.set_needs_display()


    def _create_ui(self):
        self.title_label = ui.Label(text="Match")
        self.title_label.alignment = ui.ALIGN_CENTER
        self.title_label.font = ('<system-bold>', 24)
        self.add_subview(self.title_label)

        colors = ["Red", "Orange", "Yellow", "Green", "Blue", "Purple"]
        self.color_buttons = self._create_buttons(colors, self.set_color, True)
        self.build_item_buttons()


    def build_item_buttons(self):
        for btn in self.item_buttons:
            self.remove_subview(btn)

        if self.mode == 'words':
            items = []
            letters = self.model.current_group()

            for i in range(6):
                if i < len(letters):
                    letter = letters[i]
                    items.append((letter.upper(), lambda sender, l=letter: self.spawn_item(l)))
                else:
                    items.append(("", None))

            items.append(("New Word", self.new_word))
            items.append(("Edit Words", self.edit_words))
            items.append(("Choose", self.choose_mode))
        else:
            items = []
            for item_id in self.model.current_group():
                display_name = item_id.capitalize() if self.mode == 'shapes' else item_id
                items.append((display_name, lambda sender, iid=item_id: self.spawn_item(iid)))
            items.append(("New", self.new_group))
            items.append(("Choose", self.choose_mode))

        self.item_buttons = self._create_buttons(items, None, False)


    def _create_buttons(self, items, action, colored):
        buttons = []
        for item in items:
            if isinstance(item, tuple):
                name, func = item
            else:
                name = item
                func = action

            btn = ui.Button(title=name, action=func)
            btn.corner_radius = 20

            if colored:
                btn.background_color = self.color_map.get(name, '#CCCCCC')
                btn.tint_color = 'white'
            else:
                btn.background_color = 'white'
                btn.tint_color = 'black'

            if name == "":
                btn.enabled = False
                btn.alpha = 0.3

            self.add_subview(btn)
            buttons.append(btn)
        return buttons


    def clear_board(self):
        for s in self.model.shapes:
            if hasattr(s, 'view') and s.view:
                self.remove_subview(s.view)
        self.model.shapes.clear()

        for t in self.model.targets:
            if hasattr(t, 'view') and t.view:
                self.remove_subview(t.view)
                t.view = None

        self.model.targets.clear()


    def new_group(self, sender=None):
        self.clear_board()
        self.model.next_group()          # ← Advances to next group
        self.model.init_targets()
        self.build_item_buttons()
        self._position_targets()
        self.set_needs_display()


    def new_word(self, sender=None):
        self.clear_board()
        self.model.next_group()
        self.model.init_targets()
        self.build_item_buttons()
        self._position_targets()
        self.set_needs_display()


    def _position_targets(self):
        play_top = self.UI_HEIGHT
        play_height = self.height - play_top

        if self.mode == 'words':
            word_len = len(self.model.current_word)
            spacing = self.letter_size + 20
            total_width = word_len * spacing
            start_x = (self.width - total_width) / 2 + self.letter_size / 2

            offset = 33
            if self.width > self.height:
                offset = 55

            for i, t in enumerate(self.model.targets):
                display_char = t.id.upper() if i == 0 else t.id

                t.x = start_x + i * spacing
                t.y = play_top + play_height * 0.75 + offset

                if not t.view:
                    t.view = OutlinedCharView(
                        display_char,
                        font_size=self.letter_size,
                        fill_color=None
                    )
                    self.add_subview(t.view)
                t.view.center = (t.x, t.y)
            return

        offset = 33
        if self.width > self.height:
            offset = 55
        for i, t in enumerate(self.model.targets):
            t.x = self.width * (0.1 + i * 0.2)
            t.y = play_top + play_height * 0.75 + offset
            if self.mode != 'shapes':
                if not t.view:
                    t.view = OutlinedCharView(t.id, font_size=self.letter_size, fill_color=None)
                    self.add_subview(t.view)
                t.view.center = (t.x, t.y)


    def spawn_item(self, item_id):
        if any(s for s in self.model.shapes if not s.locked):
            return

        if self.mode == 'words':
            needed = self.model.current_word.count(item_id)
            current = sum(1 for s in self.model.shapes if s.id == item_id)
            if current >= needed:
                return
        elif any(s.id == item_id for s in self.model.shapes):
            return

        play_top = self.UI_HEIGHT
        play_height = self.height - play_top
        cx = self.width / 2
        cy = play_top + play_height * 0.15 # Change spawn height

        shape = Shape(item_id, cx, cy, self.current_color)
        self.model.shapes.append(shape)

        speech.say(item_id.capitalize() if self.mode == 'shapes' else item_id)

        if self.mode != 'shapes':
            display_char = (
                item_id.upper() 
                if (self.mode == 'words' and len(self.model.shapes) == 0 and item_id == self.model.current_word[0])
                else item_id
            )
            shape.view = OutlinedCharView(display_char, font_size=self.letter_size, fill_color=shape.color)
            self.add_subview(shape.view)
            shape.view.center = (cx, cy)
        else:
            self.set_needs_display()


    def set_color(self, sender):
        self.current_color = self.color_map[sender.title]
        speech.say(sender.title)
        unlocked_shapes = [s for s in self.model.shapes if not s.locked]
        if unlocked_shapes:
            s = unlocked_shapes[0]
            s.color = self.current_color
            if self.mode != 'shapes' and s.view:
                s.view.set_fill_color(self.current_color)
            else:
                self.set_needs_display()


    def draw(self):
        ui.set_color(self.play_bg_color)
        ui.fill_rect(0, self.UI_HEIGHT, self.width, self.height - self.UI_HEIGHT)
        if self.mode != 'shapes':
            return
        for t in self.model.targets:
            matched_s = next((s for s in self.model.shapes if s.id == t.id and s.locked), None)
            self._draw_shape(t.id, t.x, t.y, 'darkgray', False)
            if matched_s:
                self._draw_shape(t.id, t.x, t.y, matched_s.color, True)
        for s in self.model.shapes:
            if not s.locked:
                self._draw_shape(s.id, s.x, s.y, s.color, True)

    def _draw_shape(self, stype, cx, cy, color, fill):
        ui.set_color(color)
        path = self._create_path(stype, cx, cy)
        if fill:
            path.fill()
        else:
            path.line_width = 8
            path.stroke()

    def _create_path(self, stype, cx, cy):
        half_size = self.shape_size / 2
        return {
            'circle': ui.Path.oval(cx - half_size, cy - half_size, self.shape_size, self.shape_size),
            'square': ui.Path.rect(cx - half_size, cy - half_size, self.shape_size, self.shape_size),
            'triangle': self._triangle_path(cx, cy, half_size),
            'star': self._star_path(cx, cy, half_size),
            'cross': self._cross_path(cx, cy, half_size)
        }[stype]

    def _triangle_path(self, cx, cy, half_size):
        side = self.shape_size
        h = side * math.sqrt(3) / 2
        p = ui.Path()
        p.move_to(cx, cy - h / 2)
        p.line_to(cx - side / 2, cy + h / 2)
        p.line_to(cx + side / 2, cy + h / 2)
        p.close()
        return p

    def _star_path(self, cx, cy, half_size):
        outer = self.shape_size * 0.6
        inner = outer * 0.5
        p = ui.Path()
        for i in range(5):
            ang = math.radians(-90 + i * 72)
            x = cx + outer * math.cos(ang)
            y = cy + outer * math.sin(ang)
            if i == 0:
                p.move_to(x, y)
            else:
                p.line_to(x, y)
            ang += math.radians(36)
            x = cx + inner * math.cos(ang)
            y = cy + inner * math.sin(ang)
            p.line_to(x, y)
        p.close()
        return p

    def _cross_path(self, cx, cy, half_size):
        s = self.shape_size / 3
        h = s / 2
        p = ui.Path()
        p.move_to(cx - h, cy - 1.5*s)
        p.line_to(cx + h, cy - 1.5*s)
        p.line_to(cx + h, cy - h)
        p.line_to(cx + 1.5*s, cy - h)
        p.line_to(cx + 1.5*s, cy + h)
        p.line_to(cx + h, cy + h)
        p.line_to(cx + h, cy + 1.5*s)
        p.line_to(cx - h, cy + 1.5*s)
        p.line_to(cx - h, cy + h)
        p.line_to(cx - 1.5*s, cy + h)
        p.line_to(cx - 1.5*s, cy - h)
        p.line_to(cx - h, cy - h)
        p.close()
        return p


    def touch_began(self, touch):
        x, y = touch.location
        if y < self.UI_HEIGHT: return

        for s in reversed(self.model.shapes):
            if s.locked: continue

            hit = False
            if self.mode == 'shapes':
                half = self.shape_size / 2
                if abs(x - s.x) <= half and abs(y - s.y) <= half:
                    hit = True
            else:
                if s.view and s.view.frame.contains_point((x, y)):
                    hit = True
                    s.view.bring_to_front()

            if hit:
                self.dragging_shape = s
                self.drag_offset = (s.x - x, s.y - y)
                self.last_hover_target = None
                break


    def touch_moved(self, touch):
        if not self.dragging_shape: return
        x, y = touch.location
        ox, oy = self.drag_offset
        s = self.dragging_shape
        s.x = x + ox
        s.y = y + oy

        half = (self.shape_size / 2 if self.mode == 'shapes' else
                (s.view.width / 2 if s.view else 0))
        s.x = max(half, min(s.x, self.width - half))
        s.y = max(self.UI_HEIGHT + half, min(s.y, self.height - half))

        if self.mode != 'shapes' and s.view:
            s.view.center = (s.x, s.y)

        closest, closest_dist = None, float('inf')
        for t in self.model.targets:
            d = math.sqrt((s.x - t.x)**2 + (s.y - t.y)**2)
            if d < closest_dist:
                closest_dist = d
                closest = t

        if closest and closest_dist < self.snap_distance:
            if closest != self.last_hover_target and closest.id != s.id:
                sound.play_effect('Error')
            self.last_hover_target = closest
        else:
            self.last_hover_target = None

        if self.mode == 'shapes':
            self.set_needs_display()


    def touch_ended(self, touch):
        if not self.dragging_shape: return

        s = self.dragging_shape
        self.dragging_shape = None
        self.last_hover_target = None

        closest = None
        closest_dist = float('inf')
        for t in self.model.targets:
            d = math.sqrt((s.x - t.x)**2 + (s.y - t.y)**2)
            if d < closest_dist:
                closest_dist = d
                closest = t

        if closest and closest_dist < self.snap_distance and closest.id == s.id:
            s.locked = True
            s.x = closest.x
            s.y = closest.y

            if self.mode != 'shapes' and s.view:
                target_center = (closest.x, closest.y)

                def on_animation_complete():
                    closest.view.set_fill_color(s.color)
                    self.remove_subview(s.view)
                    s.view = None
                    sound.play_effect('arcade:Powerup_1')

                    if self.model.is_completed():
                        ui.delay(lambda: speech.say("Good Job!"), 1.5)

                ui.animate(
                    lambda: setattr(s.view, 'center', target_center),
                    duration=0.12,
                    completion=on_animation_complete
                )
            else:
                sound.play_effect('arcade:Powerup_1')
                self.set_needs_display()
                if self.model.is_completed():
                    ui.delay(lambda: speech.say("Good Job!"), 1.5)


    def choose_mode(self, sender):
        choice = dialogs.list_dialog('Select Mode',
            ['Capital', 'Lower case', 'Numbers', 'Shapes', 'Words'])
        if not choice: return
        mode_map = {'Capital':'upper', 'Lower case':'lower', 'Numbers':'numbers',
                    'Shapes':'shapes', 'Words':'words'}
        self.set_mode(mode_map[choice])


    def set_mode(self, mode):
        if self.mode == mode: return
        self.mode = mode
        self.model.mode = mode

        if mode == 'shapes':
            self.play_bg_color = 'white'
            self.snap_distance = self.shape_size * 0.4
            self.title_label.text = "Match the Shapes!"
        elif mode == 'words':
            self.play_bg_color = '#f0f0f0'
            self.snap_distance = self.letter_size * 0.65
            self.title_label.text = "Spell the Word!"
            self.model.pick_word()
        else:
            self.play_bg_color = '#f0f0f0'
            self.snap_distance = self.letter_size * 0.8
            self.title_label.text = "Match"
            if mode == 'upper':
                self.model.alphabet = self.model.upper_alphabet
            elif mode == 'lower':
                self.model.alphabet = self.model.lower_alphabet
            else:
                self.model.alphabet = self.model.numbers_alphabet

            self.model.start_index = 0          # ← Restart from first group when switching via Choose

        self.clear_board()
        self.model.init_targets()
        self.build_item_buttons()
        self._position_targets()
        self.set_needs_display()


    def edit_words(self, sender=None):
        current_text = ", ".join(self.model.words)
        new_text = dialogs.text_dialog(title="Edit Word List (max 6 letters)", text=current_text)
        if new_text is not None:
            new_words = []
            for w in new_text.split(","):
                w = w.strip().lower()
                if w:
                    if len(w) > 6:
                        dialogs.alert("Word Too Long", 
                                      f"'{w}' has {len(w)} letters.\nMaximum allowed is 6 characters.")
                        return
                    new_words.append(w)
            if new_words:
                self.model.words = new_words
                self.new_word()


# ====================== RUN ======================

GameView()
