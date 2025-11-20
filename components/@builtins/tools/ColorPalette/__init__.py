import pygame
from libs.common.components import SolidButton
import math
import colorsys
from typing import Any, Dict, Tuple, Optional, List

# Converts HSV (Hue, Saturation, Value) color to RGB.
def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Converts HSV color values (0.0-1.0) to RGB (0-255).

    Args:
        h: Hue (0.0 to 1.0).
        s: Saturation (0.0 to 1.0).
        v: Value (0.0 to 1.0).

    Returns:
        A tuple of (R, G, B) values (0 to 255).
    """
    rgb_float: Tuple[float, float, float] = colorsys.hsv_to_rgb(h, s, v)
    return (int(rgb_float[0] * 255), int(rgb_float[1] * 255), int(rgb_float[2] * 255))

# Converts RGB color to HSV.
def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Converts RGB color values (0-255) to HSV (0.0-1.0).

    Args:
        r: Red (0 to 255).
        g: Green (0 to 255).
        b: Blue (0 to 255).

    Returns:
        A tuple of (H, S, V) values (0.0 to 1.0).
    """
    hsv_float: Tuple[float, float, float] = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return hsv_float

# Converts an RGB tuple to a hexadecimal color string.
def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    Converts an (R, G, B) tuple to a hex color string (e.g., "#RRGGBB").

    Args:
        rgb: A tuple of (R, G, B) values (0 to 255).

    Returns:
        A hex color string.
    """
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

# Creates a pygame.Surface containing a color wheel.
def create_color_wheel_surface(size: int) -> pygame.Surface:
    """
    Generates a circular color wheel (HSV) on a pygame.Surface.

    Args:
        size: The width and height of the square surface.

    Returns:
        A pygame.Surface with the color wheel drawn on it.
    """
    surface: pygame.Surface = pygame.Surface((size, size), pygame.SRCALPHA)
    radius: int = size // 2
    for y in range(size):
        for x in range(size):
            dx: int = x - radius
            dy: int = y - radius
            distance: float = math.sqrt(dx**2 + dy**2)
            if distance <= radius:
                # Calculate hue from angle
                angle: float = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
                # Calculate saturation from distance
                saturation: float = distance / radius
                rgb: Tuple[int, int, int] = hsv_to_rgb(angle, saturation, 1.0) # Value is max
                surface.set_at((x, y), (rgb[0], rgb[1], rgb[2], 255))
    return surface

# Updates HSV/RGB values based on mouse position on the color wheel or value bar.
def update_color_from_pos(mouse_pos: Tuple[int, int], hsv_in: Tuple[float, float, float], 
                          wheel_rect: pygame.Rect, bar_rect: pygame.Rect, 
                          drag_mode: str) -> Tuple[Tuple[float, float, float], Tuple[int, int, int]]:
    """
    Calculates a new color based on the mouse position within the color picker UI.

    Args:
        mouse_pos: The current (x, y) position of the mouse.
        hsv_in: The current (H, S, V) color.
        wheel_rect: The pygame.Rect of the color wheel.
        bar_rect: The pygame.Rect of the value (brightness) bar.
        drag_mode: "wheel" or "bar", indicating which component is being dragged.

    Returns:
        A tuple containing:
            - The new (H, S, V) tuple.
            - The corresponding (R, G, B) tuple.
    """
    h, s, v = hsv_in
    
    if drag_mode == "wheel":
        # Calculate new Hue and Saturation from wheel position
        dx: float = mouse_pos[0] - wheel_rect.centerx
        dy: float = mouse_pos[1] - wheel_rect.centery
        distance = math.sqrt(dx**2 + dy**2)
        radius: float = wheel_rect.width / 2
        
        s = min(distance / radius, 1.0) 
        angle: float = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
        h = angle
        
    elif drag_mode == "bar":
        # Calculate new Value from bar position
        clamped_y: int = max(bar_rect.y, min(mouse_pos[1], bar_rect.bottom - 1))
        relative_y: int = clamped_y - bar_rect.y 
        denominator: int = max(1, bar_rect.height - 1)
        v = 1.0 - (relative_y / denominator) # Y is inverted (0 at top)
        v = max(0.0, min(v, 1.0))
        
    new_hsv: Tuple[float, float, float] = (h, s, v)
    return new_hsv, hsv_to_rgb(new_hsv[0], new_hsv[1], new_hsv[2])


# Defines the ColorPalette tool for selecting colors.
class ColorPalette:
    """
    A tool for selecting a drawing color.
    It provides a popup modal with an HSV color wheel, value slider,
    color swatch, and recent color selections.
    """
    
    def __init__(self, rect: pygame.Rect, config: Dict[str, Any]):
        """
        Initializes the ColorPalette tool.

        Args:
            rect: The pygame.Rect defining the button's position and size.
            config: The configuration dictionary for this tool.
        """
        self.name: str = config['name']
        self.registryId: str = config["registryId"]
        self.config_type: str = config["type"]
        self.button: SolidButton = SolidButton(
            rect.x, rect.y, rect.width, rect.height,
            bg_color=(100,100,100), 
            font_size=20,
            icon_path=config["tool"]
        )
        self.is_drawing_tool: bool = (config["type"] == "drawing_tool") 
        
        # --- Popup Modal UI Elements ---
        self.modal_rect: pygame.Rect = pygame.Rect(0, 0, 450, 240)
        self.WHEEL_SIZE: int = 150
        self.color_wheel_surface: pygame.Surface = create_color_wheel_surface(self.WHEEL_SIZE)
        self.wheel_rect: pygame.Rect = self.color_wheel_surface.get_rect(topleft=(20, 20))
        
        self.BAR_WIDTH: int = 30
        self.BAR_HEIGHT: int = self.WHEEL_SIZE
        self.value_bar_rect: pygame.Rect = pygame.Rect(self.wheel_rect.right + 20, self.wheel_rect.y, self.BAR_WIDTH, self.BAR_HEIGHT)
        
        self.current_color_swatch_rect: pygame.Rect = pygame.Rect(self.value_bar_rect.right + 20, self.wheel_rect.y, 180, 80)
        
        self.recent_colors: List[Tuple[int, int, int]] = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 0, 0)]
        self.recent_swatches_pos: List[Tuple[int, int]] = []
        self.RECENT_SWATCH_RADIUS: int = 15
        self.swatch_gap: int = 10
        
        self.is_dragging_wheel: bool = False
        self.is_dragging_bar: bool = False
        
        self.font: pygame.font.Font
        try:
            self.font = pygame.font.Font("freesansbold.ttf", 18)
        except:
            self.font = pygame.font.Font(None, 22)

    def get_cursor_draw_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides information for drawing the cursor.
        For the ColorPalette, we just use the default system cursor.
        """
        return {"type": "custom", "radius": 0, "color": None}

    # Adds a color to the "recent colors" list.
    def add_recent_color(self, color: Tuple[int, int, int]) -> None:
        """
        Adds a color to the list of recent colors, maintaining a max of 5.

        Args:
            color: The (R, G, B) color tuple to add.
        """
        if color in self.recent_colors:
            self.recent_colors.remove(color)
        self.recent_colors.insert(0, color)
        if len(self.recent_colors) > 5:
            self.recent_colors.pop()

    # Handles user input events for the ColorPalette.
    def handle_event(self, event: pygame.event.Event, context: Dict[str, Any]) -> bool:
        """
        Processes pygame events for interacting with the color picker modal.

        Args:
            event: The pygame.event.Event to process.
            context: The shared canvas context for updating color state.

        Returns:
            True if the event was handled by this tool, False otherwise.
        """
        menu_open: Optional[str] = context.get("menu_open")
        mouse_pos: Tuple[int, int] = context.get("mouse_pos")

        # Event: Click on the tool's button in the toolbar.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button.rect.collidepoint(event.pos):
                # Toggle the color picker modal
                if context.get("menu_open") == self.registryId:
                    context["menu_open"] = None
                else:
                    context["menu_open"] = self.registryId
                    # Sync modal with current draw color
                    context["current_hsv"] = rgb_to_hsv(*context.get("draw_color", (0,0,0)))
                return True # Event handled

        # If the modal is not open, do nothing.
        if menu_open != self.registryId:
            self.is_dragging_wheel = False
            self.is_dragging_bar = False
            return False

        # --- Logic for when the color modal is open ---
        self._update_popup_rects(context) # Update modal position

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.modal_rect.collidepoint(mouse_pos): 
                drag_mode: Optional[str] = None
                if not self.is_dragging_wheel and not self.is_dragging_bar:
                    # Inflate bar rect slightly to make it easier to click
                    check_bar_rect: pygame.Rect = self.value_bar_rect.inflate(40, 10)
                    
                    if self.wheel_rect.collidepoint(mouse_pos):
                        self.is_dragging_wheel = True
                        drag_mode = "wheel"
                    elif check_bar_rect.collidepoint(mouse_pos): 
                        self.is_dragging_bar = True
                        drag_mode = "bar"
                
                # If starting a drag, update the color
                if (self.is_dragging_wheel or self.is_dragging_bar) and drag_mode:
                    hsv, rgb = update_color_from_pos(mouse_pos, context["current_hsv"], self.wheel_rect, self.value_bar_rect, drag_mode)
                    context["current_hsv"] = hsv
                    context["draw_color"] = rgb
                
                # Check for clicks on recent color swatches
                elif not (self.is_dragging_wheel or self.is_dragging_bar):
                    for i, pos in enumerate(self.recent_swatches_pos):
                        if math.dist(pos, mouse_pos) <= self.RECENT_SWATCH_RADIUS:
                            rgb = self.recent_colors[i]
                            context["draw_color"] = rgb
                            context["current_hsv"] = rgb_to_hsv(*rgb)
                            self.add_recent_color(rgb) # Move clicked color to front
                            break
                
                return True # Event handled (click inside modal)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: 
            if self.is_dragging_wheel or self.is_dragging_bar:
                # Add the newly selected color to recents
                self.add_recent_color(context["draw_color"])
                self.is_dragging_wheel = False
                self.is_dragging_bar = False
                return True # Event handled (stopped dragging)
            
            if self.modal_rect.collidepoint(mouse_pos):
                return True # Event handled (click release inside modal)

        elif event.type == pygame.MOUSEMOTION:
            # Handle dragging the wheel or bar
            drag_mode_motion: Optional[str] = None
            if self.is_dragging_wheel:
                drag_mode_motion = "wheel"
            elif self.is_dragging_bar:
                drag_mode_motion = "bar"
            
            if drag_mode_motion:
                hsv, rgb = update_color_from_pos(mouse_pos, context["current_hsv"], self.wheel_rect, self.value_bar_rect, drag_mode_motion)
                context["current_hsv"] = hsv
                context["draw_color"] = rgb
                return True # Event handled (mouse drag)
        
        # Event: Click outside the modal (close it).
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal_rect.collidepoint(mouse_pos):
                context["menu_open"] = None
                self.is_dragging_wheel = False
                self.is_dragging_bar = False
                return False
        
        # Event: Mouse is over the modal (consume it).
        if self.modal_rect.collidepoint(mouse_pos):
             return True
        
        return False

    # Updates the tool button's position.
    def update_button_pos(self, x: int, y: int) -> None:
        """
        Updates the position of the tool's button.

        Args:
            x: The new x-coordinate.
            y: The new y-coordinate.
        """
        self.button.rect.topleft = (x, y)
        if self.button.icon_surf:
            pass
        else:
            self.button.text_rect.center = self.button.rect.center

    # Draws the ColorPalette button and its modal if open.
    def draw(self, screen: pygame.Surface, context: Dict[str, Any]) -> None:
        """
        Draws the tool's button and the color picker modal (if active).

        Args:
            screen: The pygame.Surface to draw on.
            context: The shared canvas context.
        """
        menu_open: Optional[str] = context.get("menu_open")
        is_active: bool = (menu_open == self.registryId) 
        
        if is_active:
            # Draw highlight if modal is open
            pygame.draw.rect(screen, (200, 200, 0), self.button.rect.inflate(4, 4))
        
        self.button.draw(screen)
        
        # Draw a small swatch of the current color on the button
        draw_color: Tuple[int, int, int] = context.get("draw_color", (0,0,0))
        color_swatch_rect: pygame.Rect = pygame.Rect(0, 0, 15, 15)
        color_swatch_rect.topright = self.button.rect.topright
        color_swatch_rect.move_ip(-5, 5) # Inset from top-right corner
        pygame.draw.rect(screen, draw_color, color_swatch_rect)
        pygame.draw.rect(screen, (0,0,0), color_swatch_rect, 1)
        
        # Draw the color picker modal if this tool's menu is open
        if is_active:
            self._update_popup_rects(context)
            
            h, s, v = context.get("current_hsv", (0,0,0))
            
            # Draw modal background
            pygame.draw.rect(screen, (220, 220, 220), self.modal_rect)
            pygame.draw.rect(screen, (0,0,0), self.modal_rect, 2)
            
            # Draw color wheel
            screen.blit(self.color_wheel_surface, self.wheel_rect)
            
            # Draw value bar
            base_color: Tuple[int, int, int] = hsv_to_rgb(h, s, 1.0)
            for i in range(self.BAR_HEIGHT):
                bar_v: float = 1.0 - (i / self.BAR_HEIGHT)
                bar_color: Tuple[int, int, int] = hsv_to_rgb(h, s, bar_v)
                pygame.draw.line(screen, bar_color, (self.value_bar_rect.x, self.value_bar_rect.y + i), (self.value_bar_rect.right, self.value_bar_rect.y + i))
            
            # Draw wheel indicator
            indicator_x: float = self.wheel_rect.centerx + (s * (self.WHEEL_SIZE / 2) * math.cos(h * 2 * math.pi))
            indicator_y: float = self.wheel_rect.centery + (s * (self.WHEEL_SIZE / 2) * math.sin(h * 2 * math.pi))
            pygame.draw.circle(screen, (0,0,0), (indicator_x, indicator_y), 7, 2)
            pygame.draw.circle(screen, (255,255,255), (indicator_x, indicator_y), 5, 2)
            
            # Draw value bar indicator
            indicator_y_relative: float = (1.0 - v) * self.BAR_HEIGHT
            indicator_y_bar: float = self.value_bar_rect.y + indicator_y_relative
            indicator_y_clamped: int = int(max(self.value_bar_rect.y, min(indicator_y_bar, self.value_bar_rect.bottom -1)))
            pygame.draw.line(screen, (0,0,0), (self.value_bar_rect.left, indicator_y_clamped), (self.value_bar_rect.right, indicator_y_clamped), 4)
            pygame.draw.line(screen, (255,255,255), (self.value_bar_rect.left, indicator_y_clamped), (self.value_bar_rect.right, indicator_y_clamped), 2)
            
            # Draw current color swatch and info
            pygame.draw.rect(screen, draw_color, self.current_color_swatch_rect)
            pygame.draw.rect(screen, (0,0,0), self.current_color_swatch_rect, 1)

            rgb_text: str = f"RGB: {draw_color[0]}, {draw_color[1]}, {draw_color[2]}"
            hex_text: str = f"HEX: {rgb_to_hex(draw_color)}"
            rgb_surf: pygame.Surface = self.font.render(rgb_text, True, (0,0,0))
            hex_surf: pygame.Surface = self.font.render(hex_text, True, (0,0,0))
            screen.blit(rgb_surf, (self.current_color_swatch_rect.x + 10, self.current_color_swatch_rect.bottom + 10))
            screen.blit(hex_surf, (self.current_color_swatch_rect.x + 10, self.current_color_swatch_rect.bottom + 40))

            # Draw recent color swatches
            for i, pos in enumerate(self.recent_swatches_pos):
                pygame.draw.circle(screen, self.recent_colors[i], pos, self.RECENT_SWATCH_RADIUS)
                pygame.draw.circle(screen, (0,0,0), pos, self.RECENT_SWATCH_RADIUS, 1)

    # Updates the position of the color picker modal popup.
    def _update_popup_rects(self, context: Dict[str, Any]) -> None:
        """
        Private method to update the position of the color modal relative
        to the tool button and clamp it within the screen.

        Args:
            context: The shared canvas context.
        """
        toolbar_current_y: int = context["toolbar_current_y"]
        screen_rect_for_clamp: pygame.Rect = context["screen"].get_rect().inflate(-10, -10)
        
        # Position modal above the toolbar, centered on the button
        self.modal_rect.bottom = toolbar_current_y - 10
        self.modal_rect.centerx = self.button.rect.centerx
        
        # Ensure the modal stays on-screen
        self.modal_rect.clamp_ip(screen_rect_for_clamp)
        
        # Update positions of all modal elements relative to the modal rect
        self.wheel_rect.topleft = (self.modal_rect.x + 20, self.modal_rect.y + 20)
        self.value_bar_rect.topleft = (self.wheel_rect.right + 20, self.wheel_rect.y)
        self.current_color_swatch_rect.topleft = (self.value_bar_rect.right + 20, self.wheel_rect.y)
        
        self.recent_swatches_pos = []
        for i in range(5):
            x: int = self.modal_rect.x + 30 + i * (self.RECENT_SWATCH_RADIUS * 2 + self.swatch_gap)
            y: int = self.wheel_rect.bottom + 35
            self.recent_swatches_pos.append((x, y))