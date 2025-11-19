import pygame
import json
import random
import os
from typing import Optional, Any, List, Tuple, Dict, Callable, Type
from libs.common.components import SolidButton, SolidDropDown, InputBox
from libs.common.kits import components as load_kits
from libs.utils.pylog import Logger
# Import the new canvas manager
from libs.common.screens import canvasSurface

logger = Logger(__name__)

# --- Utility Functions ---

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def load_choices() -> Dict[str, List[str]]:
    path = os.path.join("src", "assets", "data", "choice.json")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load choice.json: {e}")
        return {}

# --- Global Constants ---

WORLD_WIDTH: int = 1920
WORLD_HEIGHT: int = 1080

HIGHLIGHT_COLOR_DRAWING: Tuple[int, int, int] = (255, 200, 0)
HIGHLIGHT_COLOR_CONTEXT: Tuple[int, int, int] = (160, 32, 240)

TOP_BAR_HEIGHT: int = 40
TOOLBAR_HEIGHT: int = 80
TOOLBAR_PADDING: int = 10
TOOLBAR_SLIDE_DISTANCE: int = 60

HISTORY_MENU_WIDTH: int = 300
HISTORY_MENU_PADDING: int = 5
HISTORY_ITEM_HEIGHT: int = 25
MAX_VISIBLE_HISTORY_ITEMS: int = 10 

GAME_DURATION_MS: int = 2 * 60 * 1000 # 2 minutes
SUBMIT_BTN_SHOW_TIME_MS: int = 30 * 1000 # Show button when 30s remaining

# --- Main Application Function ---

def surface(screen: pygame.Surface, background: pygame.Surface, open_file_on_start: bool = False, /) -> None:
    running: bool = True
    clock: pygame.time.Clock = pygame.time.Clock()
    
    screen_width: int = screen.get_width()
    screen_height: int = screen.get_height()
    
    # --- Quick Game State Variables ---
    # States: CATEGORY_SELECT, WORD_ROLLING, WORD_REVEAL, DRAWING, GUESSING, CHECKING_GUESS, RESULT
    game_state: str = "CATEGORY_SELECT"
    
    choice_data: Dict[str, List[str]] = load_choices()
    categories: List[str] = list(choice_data.keys())
    
    selected_category: str = ""
    target_word: str = ""
    
    # Rolling animation state
    roll_timer: int = 0
    roll_speed: int = 50 
    roll_current_index: int = 0
    roll_words_pool: List[str] = []
    
    # Timer state
    timer_start_ticks: int = 0
    time_remaining_ms: int = 0
    
    # Guessing/Result state
    guess_input_box: Optional[InputBox] = None
    user_guess: str = ""
    check_timer: int = 0
    is_correct: bool = False
    
    # --- Injection Placeholders ---
    injected_screen_to_canvas: List[Optional[Callable[[Tuple[int, int]], Tuple[float, float]]]] = [None]
    injected_canvas_to_screen: List[Optional[Callable[[Tuple[float, float]], Tuple[float, float]]]] = [None]
    injected_set_zoom: List[Optional[Callable[[float, Tuple[int, int]], None]]] = [None]
    injected_apply_constraints: List[Optional[Callable[[], None]]] = [None] 
    hand_tool_id: List[Optional[str]] = [None] 
    
    history_scroll_offset: int = 0 

    # --- Tool Method Injection System ---
    _injection_targets: Dict[str, Callable[..., None]] = {
        'hand_tool_id': 
            lambda callable_method, ToolClass, tool_instance, context: 
                hand_tool_id.__setitem__(0, callable_method(ToolClass, tool_instance, context)),
        
        'set_zoom': 
            lambda callable_method, ToolClass, tool_instance, context: 
                injected_set_zoom.__setitem__(0, lambda new_zoom, pivot_pos: callable_method(ToolClass, tool_instance, context, new_zoom, pivot_pos)),
        
        'apply_constraints': 
            lambda callable_method, ToolClass, tool_instance, context: 
                injected_apply_constraints.__setitem__(0, lambda: callable_method(ToolClass, tool_instance, context, (WORLD_WIDTH, WORLD_HEIGHT))),

        'screen_to_canvas': 
            lambda callable_method, ToolClass, tool_instance, context: 
                injected_screen_to_canvas.__setitem__(0, lambda screen_pos: callable_method(ToolClass, tool_instance, context, screen_pos)),
        
        'canvas_to_screen': 
            lambda callable_method, ToolClass, tool_instance, context: 
                injected_canvas_to_screen.__setitem__(0, lambda canvas_pos: callable_method(ToolClass, tool_instance, context, canvas_pos))
    }

    # --- UI Element Initialization ---
    toolbar_btn_size: int = 60
    toolbar_btn_gap: int = 10
    top_bar_rect: pygame.Rect = pygame.Rect(0, 0, screen_width, TOP_BAR_HEIGHT)
    toolbar_visible_y: int = screen_height - TOOLBAR_HEIGHT
    toolbar_hidden_y: int = screen_height - TOOLBAR_SLIDE_DISTANCE
    toolbar_rect: pygame.Rect = pygame.Rect(0, toolbar_visible_y, screen_width, TOOLBAR_HEIGHT)

    # --- Quick Game Specific UI ---
    
    # 1. Category Select UI
    cat_modal_rect = pygame.Rect(0, 0, 600, 400)
    cat_modal_rect.center = (screen_width // 2, screen_height // 2)
    
    cat_dropdown = SolidDropDown(
        cat_modal_rect.centerx - 175, cat_modal_rect.centery - 80, 
        350, 50, "Select Category", categories, max_visible_options=5
    )
    
    cat_submit_btn = SolidButton(
        cat_modal_rect.centerx - 75, cat_modal_rect.bottom - 80, 
        150, 50, "Start", bg_color=(0, 200, 0), text_color="White"
    )
    
    # 2. Word Reveal UI
    reveal_ok_btn = SolidButton(
        screen_width // 2 - 75, screen_height // 2 + 100,
        150, 50, "OK", bg_color=(0, 150, 255), text_color="White"
    )
    
    # 3. Drawing Phase UI
    draw_submit_btn = SolidButton(
        screen_width // 2 - 100, 60, 
        200, 50, "Submit", bg_color=(255, 100, 100), text_color="White"
    )
    
    # 4. Guessing Phase UI
    guess_panel_height = 150
    guess_panel_rect = pygame.Rect(0, screen_height - guess_panel_height, screen_width, guess_panel_height)
    
    guess_input_box = InputBox(
        screen_width // 2 - 200, screen_height - 80, 
        400, 50, numeric_only=False, font=pygame.font.Font(None, 40)
    )
    
    guess_submit_btn = SolidButton(
        guess_input_box.rect.right + 20, guess_input_box.rect.y,
        120, 50, "Submit", bg_color=(0, 200, 0), text_color="White"
    )

    # 5. Result UI
    play_again_btn = SolidButton(
        screen_width // 2 - 160, screen_height // 2 + 50,
        150, 50, "Again", bg_color=(0, 200, 0), text_color="White"
    )
    
    main_menu_btn = SolidButton(
        screen_width // 2 + 10, screen_height // 2 + 50,
        150, 50, "Back", bg_color=(200, 0, 0), text_color="White"
    )

    # Fonts
    title_font = pygame.font.Font(None, 60)
    label_font = pygame.font.Font(None, 40)
    timer_font = pygame.font.Font("freesansbold.ttf", 40) if os.path.exists("freesansbold.ttf") else pygame.font.Font(None, 40)
    result_font = pygame.font.Font(None, 100)

    # --- Canvas & History State ---
    initial_offset_x: float = (screen_width - WORLD_WIDTH) / 2
    initial_offset_y: float = (screen_height - WORLD_HEIGHT) / 2
    canvas: canvasSurface = canvasSurface(WORLD_WIDTH, WORLD_HEIGHT, max_history_size=30)
    drawing_surface: pygame.Surface = canvas.drawing_surface 
    
    # --- Wrapper Functions ---
    def update_canvas_state(new_surface: Optional[pygame.Surface]):
        nonlocal drawing_surface, shared_tool_context
        if new_surface:
            drawing_surface = new_surface
            shared_tool_context["drawing_surface"] = drawing_surface

    def add_history_and_scroll(action_name: str) -> None:
        nonlocal history_scroll_offset
        new_scroll = canvas.add_history(action_name, drawing_surface)
        if new_scroll is not None:
            history_scroll_offset = new_scroll
            
    def reset_zoom_to_fit() -> None:
        """Calculates and sets the zoom/pan to fit the world within the screen."""
        fit_zoom_w = screen_width / WORLD_WIDTH
        fit_zoom_h = screen_height / WORLD_HEIGHT
        fit_zoom = min(fit_zoom_w, fit_zoom_h) * 0.9 # 90% fill
        
        # Calculate center offset
        center_offset_x = (screen_width - (WORLD_WIDTH * fit_zoom)) / 2
        center_offset_y = (screen_height - (WORLD_HEIGHT * fit_zoom)) / 2
        
        shared_tool_context["zoom_level"] = fit_zoom
        shared_tool_context["pan_offset"] = (center_offset_x, center_offset_y)
        
        # Update ZoomTool slider if it exists
        for tool in utility_tools_to_draw:
            if hasattr(tool, 'slider'):
                tool.slider.set_value(fit_zoom)

    def undo_action() -> None:
        """Undoes the last action and updates the canvas."""
        new_surface = canvas.undo()
        update_canvas_state(new_surface)

    def redo_action() -> None:
        """Redoes the last action and updates the canvas."""
        new_surface = canvas.redo()
        update_canvas_state(new_surface)

    # --- Shared Context ---
    shared_tool_context = {
        "screen": screen,
        "draw_color": (0, 0, 0),
        "current_hsv": (0.0, 0.0, 0.0),
        "draw_size": 5,
        "eraser_size": 50,
        "active_tool_id": "none",
        "is_drawing": False,
        "menu_open": None,
        "click_on_ui": False,
        "mouse_pos": (0,0),
        "toolbar_current_y": toolbar_rect.y,
        "drawing_surface": drawing_surface,
        "add_history": add_history_and_scroll,
        "zoom_level": 1.0,  
        "pan_offset": (initial_offset_x, initial_offset_y), 
        "canvas_mouse_pos": (0, 0),
        "is_panning": False,
        "pan_start_pos": (0, 0),
        "pan_start_offset": (0, 0),
        "previous_tool_id": "none"
    }
    
    # --- Tool Loading ---
    loaded_tool_plugins: List[Tuple[Dict[str, Any], Type]] = load_kits()
    tool_id_to_instance: Dict[str, Any] = {} 
    loaded_tool_instances: List[Any] = [] 
    utility_tools_to_draw: List[Any] = [] 
    utility_tools_to_update_pos: List[Any] = []
    
    toolbar_btn_x: int = TOOLBAR_PADDING
    zoom_slider_x_start: int = 0 
    first_drawing_tool_id: Optional[str] = None 

    for config, ToolClass in loaded_tool_plugins:
        btn_rect = pygame.Rect(toolbar_btn_x, toolbar_hidden_y + 10, toolbar_btn_size, toolbar_btn_size)
        tool_instance = ToolClass(btn_rect, config)
        tool_instance.config = config
        tool_id_to_instance[tool_instance.registryId] = tool_instance

        if tool_instance.config.get('type') == "utility_tool": 
            utility_tools_to_draw.append(tool_instance)
            utility_tools_to_update_pos.append(tool_instance)
            if hasattr(ToolClass, 'INJECT_METHODS'):
                for name, injected_method in config.get("injected_methods", {}).items():
                    callable_method: Callable[..., Any] = getattr(injected_method, '__func__', injected_method)
                    dispatch_func: Optional[Callable[..., None]] = _injection_targets.get(name)
                    if dispatch_func:
                        dispatch_func(callable_method, ToolClass, tool_instance, shared_tool_context)
        else:
            loaded_tool_instances.append(tool_instance)
            toolbar_btn_x += toolbar_btn_size + toolbar_btn_gap
            if first_drawing_tool_id is None and tool_instance.config.get('type') == 'drawing_tool':
                 first_drawing_tool_id = tool_instance.registryId
            
    zoom_slider_x_start = toolbar_btn_x + 10 
    
    # Validation
    if injected_screen_to_canvas[0] is None:
        raise RuntimeError("FATAL ERROR: Canvas Systems failed to inject.")
    
    # Cursor Loading
    for tool in loaded_tool_instances:
        tool.custom_cursor_surf = None
        cursor_config = tool.config.get("cursor", {})
        if cursor_config and cursor_config.get("icon"):
            try:
                cursor_surf = pygame.image.load(cursor_config.get("icon")).convert_alpha()
                cursor_size = cursor_config.get("size", cursor_surf.get_size())
                cursor_surf = pygame.transform.smoothscale(cursor_surf, cursor_size)
                hotspot_config = cursor_config.get("hotspot")
                hotspot = (cursor_surf.get_width() // 2, cursor_surf.get_height() // 2) if hotspot_config == "center" else (0,0)
                tool.custom_cursor_surf = cursor_surf
                tool.custom_cursor_hotspot = hotspot
                tool.custom_cursor_offset = cursor_config.get("offset", (0, 0))
            except: pass

    if first_drawing_tool_id:
         shared_tool_context["active_tool_id"] = first_drawing_tool_id
         shared_tool_context["previous_tool_id"] = first_drawing_tool_id
    
    shared_tool_context["active_tool_id"] = "none" # Block tools initially

    # =================================================================================
    # --- MAIN GAME LOOP ---
    # =================================================================================
    while running:
        current_time = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()
        
        shared_tool_context["mouse_pos"] = mouse_pos
        shared_tool_context["click_on_ui"] = False
        
        # --- State-Specific Logic Updates ---
        
        if game_state == "CATEGORY_SELECT":
            pass
            
        elif game_state == "WORD_ROLLING":
            if current_time - roll_timer > roll_speed:
                roll_timer = current_time
                if roll_speed < 300: roll_speed += 10
                elif roll_speed < 600: roll_speed += 50
                
                roll_current_index = (roll_current_index + 1) % len(roll_words_pool)
                
                if roll_speed >= 500 and roll_words_pool[roll_current_index] == target_word:
                    game_state = "WORD_REVEAL"
        
        elif game_state == "DRAWING":
            elapsed = current_time - timer_start_ticks
            time_remaining_ms = max(0, GAME_DURATION_MS - elapsed)
            
            if time_remaining_ms <= 0:
                # Timeout - Go to Guessing, disable tools, zoom fit
                game_state = "GUESSING"
                shared_tool_context["active_tool_id"] = "none"
                reset_zoom_to_fit()
        
        elif game_state == "CHECKING_GUESS":
            # Wait 5 seconds before showing result
            if current_time - check_timer > 5000:
                game_state = "RESULT"
                
        # --- Event Handling ---
        
        for event in events[:]:
            if event.type == pygame.QUIT:
                running = False
                continue
            
            # --- Keyboard Shortcuts (Global or State-Specific) ---
            if game_state == "DRAWING" and event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                is_ctrl_or_cmd = bool(mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META)
                is_shift = bool(mods & pygame.KMOD_SHIFT)
                
                # Undo (Ctrl+Z)
                if event.key == pygame.K_z and is_ctrl_or_cmd and not is_shift:
                    undo_action()
                # Redo (Ctrl+Y or Ctrl+Shift+Z)
                elif (event.key == pygame.K_y and is_ctrl_or_cmd) or (event.key == pygame.K_z and is_ctrl_or_cmd and is_shift):
                    redo_action()
                
                # Pan shortcut
                if event.key == pygame.K_SPACE:
                     if hand_tool_id[0] and shared_tool_context["active_tool_id"] != hand_tool_id[0]:
                         shared_tool_context["previous_tool_id"] = shared_tool_context["active_tool_id"]
                         shared_tool_context["active_tool_id"] = hand_tool_id[0]
            
            if game_state == "DRAWING" and event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    if hand_tool_id[0] and shared_tool_context["active_tool_id"] == hand_tool_id[0]:
                         shared_tool_context["active_tool_id"] = shared_tool_context["previous_tool_id"]
                         shared_tool_context["is_panning"] = False

            # Handle UI Clicks depending on State
            
            if game_state == "CATEGORY_SELECT":
                shared_tool_context["click_on_ui"] = True 
                
                selected = cat_dropdown.handle_event(event)
                if selected: selected_category = selected
                
                if not cat_dropdown.is_open:
                    if cat_submit_btn.is_clicked(event):
                        if selected_category:
                            game_state = "WORD_ROLLING"
                            roll_words_pool = choice_data[selected_category]
                            target_word = random.choice(roll_words_pool)
                            roll_speed = 30
                            roll_timer = current_time
                            roll_current_index = 0 # <--- RESET INDEX HERE
                continue

            elif game_state == "WORD_ROLLING":
                shared_tool_context["click_on_ui"] = True 
                continue

            elif game_state == "WORD_REVEAL":
                shared_tool_context["click_on_ui"] = True
                if reveal_ok_btn.is_clicked(event):
                    game_state = "DRAWING"
                    timer_start_ticks = pygame.time.get_ticks()
                    shared_tool_context["active_tool_id"] = first_drawing_tool_id or "none"
                    # Zoom to 1.0 for drawing
                    shared_tool_context["zoom_level"] = 1.0
                    shared_tool_context["pan_offset"] = (initial_offset_x, initial_offset_y)
                    for tool in utility_tools_to_draw:
                         if hasattr(tool, 'slider'): tool.slider.set_value(1.0)
                continue

            elif game_state == "DRAWING":
                if time_remaining_ms <= SUBMIT_BTN_SHOW_TIME_MS:
                    if draw_submit_btn.is_clicked(event):
                        game_state = "GUESSING"
                        shared_tool_context["active_tool_id"] = "none"
                        shared_tool_context["click_on_ui"] = True
                        reset_zoom_to_fit()
                    
                    if draw_submit_btn.rect.collidepoint(mouse_pos):
                        shared_tool_context["click_on_ui"] = True

            elif game_state == "GUESSING":
                shared_tool_context["click_on_ui"] = True 
                changed, text = guess_input_box.handle_event(event)
                
                if len(text) > 0 and guess_submit_btn.is_clicked(event):
                    user_guess = text
                    game_state = "CHECKING_GUESS"
                    check_timer = current_time
                    # Check logic (ignore case)
                    is_correct = (user_guess.strip().lower() == target_word.strip().lower())
                continue
            
            elif game_state == "CHECKING_GUESS":
                shared_tool_context["click_on_ui"] = True
                continue
                
            elif game_state == "RESULT":
                shared_tool_context["click_on_ui"] = True
                if play_again_btn.is_clicked(event):
                    # Reset Game
                    game_state = "CATEGORY_SELECT"
                    selected_category = ""
                    target_word = ""
                    guess_input_box.set_text("")
                    update_canvas_state(canvas.clear_canvas())
                    # Reset camera
                    shared_tool_context["zoom_level"] = 1.0
                    shared_tool_context["pan_offset"] = (initial_offset_x, initial_offset_y)
                    
                if main_menu_btn.is_clicked(event):
                    running = False
                continue

            # --- Standard Tool/Canvas Events (Only if in DRAWING state) ---
            if game_state == "DRAWING":
                
                if event.type == pygame.MOUSEWHEEL:
                    if top_bar_rect.collidepoint(mouse_pos) or toolbar_rect.collidepoint(mouse_pos):
                        shared_tool_context["click_on_ui"] = True
                
                if shared_tool_context["click_on_ui"]:
                    if event in events: events.remove(event)
                    continue

                for tool in utility_tools_to_draw:
                    if tool.handle_event(event, shared_tool_context):
                        shared_tool_context["click_on_ui"] = True
                        break
                
                if shared_tool_context["click_on_ui"]:
                    if event in events: events.remove(event)
                    continue

                tool_menu_is_open = False
                menu_open_id = shared_tool_context["menu_open"]
                if menu_open_id in tool_id_to_instance:
                    tool = tool_id_to_instance[menu_open_id]
                    tool_menu_is_open = True
                    if tool.handle_event(event, shared_tool_context):
                        shared_tool_context["click_on_ui"] = True
                
                if tool_menu_is_open:
                    if event in events: events.remove(event)
                    continue 

                tool_button_was_clicked = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for tool in loaded_tool_instances:
                        if hasattr(tool, 'button') and tool.button.rect.collidepoint(event.pos):
                            if tool.handle_event(event, shared_tool_context):
                                shared_tool_context["click_on_ui"] = True
                                tool_button_was_clicked = True
                            break
                if tool_button_was_clicked:
                    if event in events: events.remove(event)
                    continue

                if not shared_tool_context["click_on_ui"]:
                    active_tool_instance = tool_id_to_instance.get(shared_tool_context.get("active_tool_id"))
                    if active_tool_instance:
                        # Only handle if NOT a keyboard event we already processed
                        if not (event.type == pygame.KEYUP and event.key == pygame.K_SPACE) and \
                           not (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                                if active_tool_instance.handle_event(event, shared_tool_context):
                                    if event in events: events.remove(event)

        # --- Toolbar Position Logic ---
        if game_state == "DRAWING":
            is_drawing = shared_tool_context["is_drawing"]
            if shared_tool_context["menu_open"] is not None:
                 target_y = toolbar_visible_y
            elif is_drawing:
                 target_y = toolbar_hidden_y
            else:
                 if mouse_pos[1] > screen_height - 20 or toolbar_rect.collidepoint(mouse_pos):
                     target_y = toolbar_visible_y
                 else:
                     target_y = toolbar_hidden_y
        else:
             target_y = toolbar_hidden_y

        toolbar_rect.y = round(lerp(toolbar_rect.y, target_y, 0.2))
        shared_tool_context["toolbar_current_y"] = toolbar_rect.y
        
        for tool in loaded_tool_instances:
            if hasattr(tool, 'button'): tool.update_button_pos(tool.button.rect.x, toolbar_rect.y + 10)
        for tool in utility_tools_to_update_pos: tool.update_button_pos(zoom_slider_x_start, toolbar_rect.y + 25)
        
        if injected_apply_constraints[0]: injected_apply_constraints[0]()

        # =================================================================================
        # --- DRAWING / RENDERING ---
        # =================================================================================
        
        screen.fill((80, 80, 80))
        
        # 1. Draw Canvas
        if injected_screen_to_canvas[0] and injected_canvas_to_screen[0]:
            tl = injected_screen_to_canvas[0]((0,0))
            br = injected_screen_to_canvas[0]((screen_width, screen_height))
            vis_rect = pygame.Rect(tl, (br[0]-tl[0], br[1]-tl[1])).clip(drawing_surface.get_rect())
            if vis_rect.w > 0 and vis_rect.h > 0:
                sub = drawing_surface.subsurface(vis_rect)
                dest = injected_canvas_to_screen[0](vis_rect.topleft)
                zoom = shared_tool_context["zoom_level"]
                scaled = pygame.transform.scale(sub, (int(vis_rect.w * zoom), int(vis_rect.h * zoom)))
                screen.blit(scaled, dest)

        # 2. Draw Cursors
        is_on_canvas = (
            game_state == "DRAWING" and
            not top_bar_rect.collidepoint(mouse_pos) and
            not toolbar_rect.collidepoint(mouse_pos) and
            shared_tool_context["menu_open"] is None and
            not shared_tool_context["click_on_ui"]
        )
        
        # Default to system arrow
        pygame.mouse.set_visible(True)
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if hand_tool_id[0] and shared_tool_context["is_panning"] and shared_tool_context.get("active_tool_id") == hand_tool_id[0]:
             active_tool_instance = tool_id_to_instance.get(hand_tool_id[0])
             if active_tool_instance:
                 pygame.mouse.set_visible(False)
                 if active_tool_instance.custom_cursor_surf:
                     hotspot_x = mouse_pos[0] - active_tool_instance.custom_cursor_hotspot[0]
                     hotspot_y = mouse_pos[1] - active_tool_instance.custom_cursor_hotspot[1]
                     offset_x = active_tool_instance.custom_cursor_offset[0]
                     offset_y = active_tool_instance.custom_cursor_offset[1]
                     draw_pos = (hotspot_x + offset_x, hotspot_y + offset_y)
                     screen.blit(active_tool_instance.custom_cursor_surf, draw_pos)
                 else:
                     pygame.mouse.set_visible(True)
        
        elif is_on_canvas:
            active_tool_instance = tool_id_to_instance.get(shared_tool_context.get("active_tool_id"))
            if active_tool_instance:
                cursor_info = active_tool_instance.get_cursor_draw_info(shared_tool_context)
                cursor_type = cursor_info.get("type", "custom")

                if active_tool_instance.is_drawing_tool and cursor_type in ["custom", "circle"]:
                    radius = cursor_info.get("radius", 1)
                    fill_color = cursor_info.get("color", (0, 0, 0))
                    screen_radius = max(1, int(radius * shared_tool_context["zoom_level"]))
                    
                    pygame.mouse.set_visible(False)
                    pygame.draw.circle(screen, fill_color, mouse_pos, screen_radius)
                    pygame.draw.circle(screen, (0, 0, 0), mouse_pos, screen_radius, width=2)
                    if screen_radius > 3:
                         pygame.draw.circle(screen, (255, 255, 255), mouse_pos, screen_radius - 2, width=1)

                if active_tool_instance.custom_cursor_surf:
                     pygame.mouse.set_visible(False)
                     hotspot_x = mouse_pos[0] - active_tool_instance.custom_cursor_hotspot[0]
                     hotspot_y = mouse_pos[1] - active_tool_instance.custom_cursor_hotspot[1]
                     offset_x = active_tool_instance.custom_cursor_offset[0]
                     offset_y = active_tool_instance.custom_cursor_offset[1]
                     draw_pos = (hotspot_x + offset_x, hotspot_y + offset_y)
                     screen.blit(active_tool_instance.custom_cursor_surf, draw_pos)

        # 3. Draw UI Overlays
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        
        if game_state == "CATEGORY_SELECT":
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0,0))
            
            pygame.draw.rect(screen, (240, 240, 240), cat_modal_rect, border_radius=15)
            pygame.draw.rect(screen, (50, 50, 50), cat_modal_rect, 3, border_radius=15)
            
            title = label_font.render("Choose a Category", True, "Black")
            screen.blit(title, title.get_rect(center=(cat_modal_rect.centerx, cat_modal_rect.top + 40)))
            
            if selected_category:
                cat_submit_btn.draw(screen)
            cat_dropdown.draw(screen)

        elif game_state == "WORD_ROLLING":
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0,0))
            
            current_word = roll_words_pool[roll_current_index]
            text_surf = title_font.render(current_word, True, "White")
            screen.blit(text_surf, text_surf.get_rect(center=(screen_width//2, screen_height//2)))
            
            status = label_font.render("Choosing...", True, (200, 200, 200))
            screen.blit(status, status.get_rect(center=(screen_width//2, screen_height//2 - 60)))

        elif game_state == "WORD_REVEAL":
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0,0))
            
            lbl = label_font.render("You must draw:", True, (200, 200, 200))
            screen.blit(lbl, lbl.get_rect(center=(screen_width//2, screen_height//2 - 60)))
            
            word_surf = pygame.font.Font(None, 100).render(target_word, True, (255, 215, 0))
            screen.blit(word_surf, word_surf.get_rect(center=(screen_width//2, screen_height//2)))
            
            reveal_ok_btn.draw(screen)

        elif game_state == "DRAWING":
            pygame.draw.rect(screen, (80, 80, 80), toolbar_rect)
            
            active_tool_id = shared_tool_context.get("active_tool_id")
            for tool in loaded_tool_instances:
                if hasattr(tool, 'button'): 
                     tool_type = tool.config.get('type')
                     highlight_color = (0,0,0)
                     if tool_type == 'drawing_tool': highlight_color = HIGHLIGHT_COLOR_DRAWING
                     elif tool_type == 'context_tool': highlight_color = HIGHLIGHT_COLOR_CONTEXT
                     
                     is_active = tool.registryId == active_tool_id
                     is_menu_open = shared_tool_context.get("menu_open") == tool.registryId
                     
                     if is_active or is_menu_open:
                         pygame.draw.rect(screen, highlight_color, tool.button.rect.inflate(4, 4))

                     tool.draw(screen, shared_tool_context)
            for tool in utility_tools_to_draw: tool.draw(screen, shared_tool_context)
            
            timer_color = (0, 255, 0) if time_remaining_ms > 30000 else (255, 0, 0)
            seconds_left = time_remaining_ms // 1000
            timer_text = f"{seconds_left // 60}:{seconds_left % 60:02}"
            timer_surf = timer_font.render(timer_text, True, timer_color)
            timer_rect = timer_surf.get_rect(center=(screen_width//2, 30))
            
            timer_bg_rect = timer_rect.inflate(20, 10)
            pygame.draw.rect(screen, (0,0,0,150), timer_bg_rect, border_radius=10)
            screen.blit(timer_surf, timer_rect)
            
            if time_remaining_ms <= SUBMIT_BTN_SHOW_TIME_MS:
                draw_submit_btn.draw(screen)

        elif game_state == "GUESSING" or game_state == "CHECKING_GUESS" or game_state == "RESULT":
            # Draw the guessing panel (keep it visible during checking/result for context)
            pygame.draw.rect(screen, (50, 50, 50), guess_panel_rect)
            pygame.draw.line(screen, (255, 255, 255), guess_panel_rect.topleft, guess_panel_rect.topright, 2)
            
            cat_text = label_font.render(f"Category: {selected_category}", True, (200, 200, 200))
            screen.blit(cat_text, (guess_panel_rect.x + 20, guess_panel_rect.y + 15))
            
            prompt_text = label_font.render("What do you guess?", True, "White")
            screen.blit(prompt_text, (guess_panel_rect.x + 20, guess_panel_rect.y + 50))
            
            guess_input_box.draw(screen)
            
            # Hide submit button if in checking/result state
            if game_state == "GUESSING" and len(guess_input_box.get_text()) > 0:
                guess_submit_btn.draw(screen)
            
            if game_state == "CHECKING_GUESS":
                # Popup "Checking..."
                overlay.fill((0, 0, 0, 150))
                screen.blit(overlay, (0, 0))
                
                check_text = title_font.render("Checking...", True, "White")
                screen.blit(check_text, check_text.get_rect(center=(screen_width // 2, screen_height // 2)))
                
            elif game_state == "RESULT":
                # Result Overlay
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (0, 0))
                
                res_color = (0, 255, 0) if is_correct else (255, 0, 0)
                res_text = "Correct!" if is_correct else "Wrong!"
                res_surf = result_font.render(res_text, True, res_color)
                screen.blit(res_surf, res_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 50)))
                
                ans_text = label_font.render(f"Answer: {target_word}", True, "White")
                screen.blit(ans_text, ans_text.get_rect(center=(screen_width // 2, screen_height // 2 + 10)))
                
                play_again_btn.draw(screen)
                main_menu_btn.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    pygame.mouse.set_visible(True)