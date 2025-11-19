import pygame
from libs.common.components import SolidSlider
from libs.interfaces.typing import Vector2DLike, Adapter
from typing import Any, Dict, Tuple, List, ClassVar, Callable, Optional

# --- Constants ---
MIN_ZOOM: float = 0.5
MAX_ZOOM: float = 2.0

# --- Coordinate Conversion Functions ---

# Converts screen coordinates to canvas (world) coordinates.
def simple_screen_to_canvas(screen_pos: Vector2DLike, zoom: float, offset: Vector2DLike) -> Tuple[float, float]:
    """
    Converts a position from screen space to canvas (world) space.

    Args:
        screen_pos: The (x, y) position on the screen.
        zoom: The current zoom level.
        offset: The current pan offset (top-left corner of canvas relative to screen).

    Returns:
        The corresponding (x, y) position on the canvas.
    """
    screen_pos_tuple = Adapter(screen_pos, 'Tuple')
    offset_tuple = Adapter(offset, 'Tuple')
    return (
        (screen_pos_tuple[0] - offset_tuple[0]) / zoom, 
        (screen_pos_tuple[1] - offset_tuple[1]) / zoom
    )

# Converts canvas (world) coordinates to screen coordinates.
def simple_canvas_to_screen(canvas_pos: Vector2DLike, zoom: float, offset: Vector2DLike) -> Tuple[float, float]:
    """
    Converts a position from canvas (world) space to screen space.

    Args:
        canvas_pos: The (x, y) position on the canvas.
        zoom: The current zoom level.
        offset: The current pan offset.

    Returns:
        The corresponding (x, y) position on the screen.
    """
    canvas_pos_tuple = Adapter(canvas_pos, 'Tuple')
    offset_tuple = Adapter(offset, 'Tuple')
    return (
        (canvas_pos_tuple[0] * zoom) + offset_tuple[0], 
        (canvas_pos_tuple[1] * zoom) + offset_tuple[1]
    )

# --- Injected Methods ---
# These methods are wrapped to be injected into the main canvas controller.

# Injected version of screen_to_canvas.
@classmethod
def screen_to_canvas_injected(cls: Any, instance: 'ZoomTool', context: Dict[str, Any], screen_pos: Vector2DLike) -> Tuple[float, float]:
    """
    Class method wrapper for simple_screen_to_canvas to be injected into the canvas.
    Retrieves zoom and offset from the shared context.
    """
    zoom: float = context["zoom_level"]
    offset: Vector2DLike = context["pan_offset"]
    return simple_screen_to_canvas(screen_pos, zoom, offset)

# Injected version of canvas_to_screen.
@classmethod
def canvas_to_screen_injected(cls: Any, instance: 'ZoomTool', context: Dict[str, Any], canvas_pos: Vector2DLike) -> Tuple[float, float]:
    """
    Class method wrapper for simple_canvas_to_screen to be injected into the canvas.
    Retrieves zoom and offset from the shared context.
    """
    zoom: float = context["zoom_level"]
    offset: Vector2DLike = context["pan_offset"]
    return simple_canvas_to_screen(canvas_pos, zoom, offset)


# Defines the ZoomTool, a utility for handling zoom and pan.
class ZoomTool:
    """
    A utility tool that provides zoom and pan functionality.
    It injects core methods (coordinate conversion, zoom control, constraints)
    into the main canvas system. It also provides a visible zoom slider UI.
    """
    
    # Injected method to set the zoom level.
    @classmethod
    def canvas_set_zoom(cls: Any, instance: 'ZoomTool', context: Dict[str, Any], new_zoom: float, pivot_pos: Vector2DLike) -> None:
        """
        Class method wrapper for _set_zoom to be injected into the canvas.
        Allows other tools or the canvas itself to request a zoom change.
        """
        instance._set_zoom(context, new_zoom, pivot_pos)

    # Injected method to apply movement/zoom constraints.
    @classmethod
    def canvas_apply_constraints(cls: Any, instance: 'ZoomTool', context: Dict[str, Any], world_size: Vector2DLike) -> None:
        """
        Class method wrapper for apply_constraints to be injected into the canvas.
        Ensures the canvas view stays within bounds.
        """
        instance.apply_constraints(context, world_size)

    # Dictionary of methods to be injected into the canvas system.
    INJECT_METHODS: Dict[str, Callable[..., Any]] = {
        'set_zoom': canvas_set_zoom,
        'apply_constraints': canvas_apply_constraints,
        'screen_to_canvas': screen_to_canvas_injected, 
        'canvas_to_screen': canvas_to_screen_injected
    }
    
    def __init__(self, rect: pygame.Rect, config: Dict[str, Any]):
        """
        Initializes the ZoomTool utility.

        Args:
            rect: The base pygame.Rect for positioning the UI (slider).
            config: The configuration dictionary for this tool.
        """
        self.name: str = config['name']
        self.registryId: str = config["registryId"]
        self.config_type: str = config["type"]
        self.is_drawing_tool: bool = False

        self.min_zoom: float = MIN_ZOOM
        self.max_zoom: float = MAX_ZOOM

        self.rect: pygame.Rect = pygame.Rect(rect.x, rect.y, 340, 30) # Overall rect for the UI
        
        # The visible slider component
        self.slider: SolidSlider = SolidSlider(
            x=self.rect.x, y=self.rect.y, 
            width=260, height=25,
            min_val=self.min_zoom, max_val=self.max_zoom, initial_val=1.0,
        )
        
        self.is_panning: bool = False
        self.pan_start_pos: Vector2DLike = (0, 0)
        self.pan_start_offset: Vector2DLike = (0, 0)

        self.font: pygame.font.Font
        try:
            self.font = pygame.font.Font("freesansbold.ttf", 20)
        except:
            self.font = pygame.font.Font(None, 20)

    # Core logic for setting the zoom level.
    def _set_zoom(self, context: Dict[str, Any], new_zoom: float, pivot_pos: Vector2DLike) -> None:
        """
        Sets the zoom level, pivoting around a specific screen position
        (e.g., the mouse cursor) to create a "zoom to point" effect.

        Args:
            context: The shared canvas context.
            new_zoom: The target zoom level.
            pivot_pos: The (x, y) screen position to zoom towards/away from.
        """
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
        
        current_zoom: float = context["zoom_level"]
        current_offset: Vector2DLike = context["pan_offset"]
        
        # Find what point on the canvas is under the pivot position
        canvas_pivot: Tuple[float, float] = simple_screen_to_canvas(pivot_pos, current_zoom, current_offset)
        
        pivot_pos_tuple = Adapter(pivot_pos, 'Tuple')
        
        # Calculate the new offset to keep the canvas_pivot at the same screen_pos
        new_offset: Tuple[float, float] = (
            pivot_pos_tuple[0] - (canvas_pivot[0] * new_zoom),
            pivot_pos_tuple[1] - (canvas_pivot[1] * new_zoom)
        )

        context["zoom_level"] = new_zoom
        context["pan_offset"] = new_offset
        self.slider.set_value(new_zoom) # Sync the UI slider

    # Applies constraints to keep the canvas view within bounds.
    def apply_constraints(self, context: Dict[str, Any], world_size: Vector2DLike) -> None:
        """
        Adjusts the pan_offset and zoom_level to ensure the canvas
        doesn't move too far out of view.

        Args:
            context: The shared canvas context.
            world_size: The (width, height) of the total canvas.
        """
        screen_width: int = context["screen"].get_width()
        screen_height: int = context["screen"].get_height()
        world_width, world_height = Adapter(world_size, 'Tuple')
        
        zoom: float = context["zoom_level"]
        offset: Vector2DLike = context["pan_offset"]
        offset_tuple = Adapter(offset, 'Tuple')

        zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        
        # --- Calculate X-axis constraints ---
        max_offset_x: float = 0 # Cannot pan further left than screen edge
        min_offset_x: float = screen_width - (world_width * zoom)
        
        # If canvas is smaller than screen, center it
        if min_offset_x > max_offset_x: 
            center_x: float = (screen_width - world_width * zoom) / 2
            min_offset_x, max_offset_x = center_x, center_x
            
        # --- Calculate Y-axis constraints ---
        max_offset_y: float = 0 # Cannot pan further up than screen edge
        min_offset_y: float = screen_height - (world_height * zoom)
        
        # If canvas is smaller than screen, center it
        if min_offset_y > max_offset_y: 
             center_y: float = (screen_height - world_height * zoom) / 2
             min_offset_y, max_offset_y = center_y, center_y

        # Apply clamped offset
        new_offset_x: float = max(min_offset_x, min(max_offset_x, offset_tuple[0]))
        new_offset_y: float = max(min_offset_y, min(max_offset_y, offset_tuple[1]))
        
        context["zoom_level"] = zoom
        context["pan_offset"] = (new_offset_x, new_offset_y)
        
        # Re-calculate the canvas mouse position after applying constraints
        canvas_mouse_pos: Tuple[float, float] = simple_screen_to_canvas(context["mouse_pos"], zoom, (new_offset_x, new_offset_y))
        context["canvas_mouse_pos"] = canvas_mouse_pos

    # Handles user input events for zoom/pan.
    def handle_event(self, event: pygame.event.Event, context: Dict[str, Any]) -> bool:
        """
        Processes pygame events for the slider, mouse wheel zooming,
        middle-mouse-button panning, and keyboard shortcuts.

        Args:
            event: The pygame.event.Event to process.
            context: The shared canvas context.

        Returns:
            True if the event was handled by this tool, False otherwise.
        """
        mouse_pos: Vector2DLike = context["mouse_pos"]
        
        # Event: Interact with the zoom slider UI.
        if self.slider.handle_event(event):
            new_zoom: float = self.slider.get_value()
            screen_center: Tuple[float, float] = (context["screen"].get_width() / 2, context["screen"].get_height() / 2)
            self._set_zoom(context, new_zoom, screen_center) # Zoom from center
            return True # Event handled

        # Event: Start panning (Middle mouse button down).
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self.is_panning = True
            context["is_panning"] = True
            self.pan_start_pos = mouse_pos
            context["pan_start_offset"] = context["pan_offset"]
            self.pan_start_offset = context["pan_offset"]
            return True # Event handled
            
        # Event: Stop panning (Middle mouse button up).
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.is_panning = False
            context["is_panning"] = False
            return True # Event handled
            
        # Event: Pan (Mouse motion while middle button is down).
        elif event.type == pygame.MOUSEMOTION:
            if self.is_panning:
                mouse_pos_tuple = Adapter(mouse_pos, 'Tuple')
                pan_start_pos_tuple = Adapter(self.pan_start_pos, 'Tuple')
                pan_start_offset_tuple = Adapter(self.pan_start_offset, 'Tuple')

                delta_x: float = mouse_pos_tuple[0] - pan_start_pos_tuple[0]
                delta_y: float = mouse_pos_tuple[1] - pan_start_pos_tuple[1]
                
                context["pan_offset"] = (
                    pan_start_offset_tuple[0] + delta_x,
                    pan_start_offset_tuple[1] + delta_y
                )
                return True # Event handled
        
        # --- NEW: Pinch-to-Zoom (Trackpad) ---
        # This event handles multi-finger pinch gestures
        if event.type == pygame.MULTIGESTURE:
            if event.pinched: # A non-zero/non-one value indicates a pinch
                current_zoom: float = context["zoom_level"]
                # event.pinched is a relative multiplier (e.g., 1.1x or 0.9x)
                new_zoom: float = current_zoom * event.pinched 
                
                # Get screen dimensions from context
                screen_width: int = context["screen"].get_width()
                screen_height: int = context["screen"].get_height()
                
                # Convert normalized gesture center (0.0-1.0) to screen pixels
                # This is the pivot point for the zoom
                pivot_pos: Tuple[float, float] = (
                    event.x * screen_width,
                    event.y * screen_height
                )
                
                self._set_zoom(context, new_zoom, pivot_pos)
                return True # Event handled
        # --- End of new code ---

        # Event: Zoom (Mouse wheel scroll).
        if event.type == pygame.MOUSEWHEEL:
            is_over_ui: bool = False
            mouse_pos_tuple = Adapter(mouse_pos, 'Tuple')
            
            # Check if mouse is over the top bar or toolbar
            if pygame.Rect(0, 0, context["screen"].get_width(), 40).collidepoint(mouse_pos_tuple):
                is_over_ui = True
            elif pygame.Rect(0, context["toolbar_current_y"], context["screen"].get_width(), 80).collidepoint(mouse_pos_tuple):
                is_over_ui = True
            
            # Only zoom if not over UI elements
            if not is_over_ui:
                current_zoom: float = context["zoom_level"]
                if event.y > 0: # Scroll up
                    self._set_zoom(context, min(MAX_ZOOM, current_zoom + 0.1), mouse_pos)
                elif event.y < 0: # Scroll down
                    self._set_zoom(context, max(MIN_ZOOM, current_zoom - 0.1), mouse_pos)
                return True # Event handled

        # Event: Keyboard shortcuts for zoom.
        if event.type == pygame.KEYDOWN:
            mods: int = pygame.key.get_mods()
            is_ctrl_or_cmd: bool = bool(mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META)
            
            if is_ctrl_or_cmd:
                if event.key == pygame.K_0: # Ctrl+0: Reset zoom
                    self._set_zoom(context, 1.0, mouse_pos)
                    return True # Event handled
                elif event.key == pygame.K_EQUALS: # Ctrl+=: Zoom in
                    self._set_zoom(context, min(MAX_ZOOM, context["zoom_level"] + 0.05), mouse_pos)
                    return True # Event handled
                elif event.key == pygame.K_MINUS: # Ctrl+-: Zoom out
                    self._set_zoom(context, max(MIN_ZOOM, context["zoom_level"] - 0.05), mouse_pos)
                    return True # Event handled

        return False # Event not handled

    # Updates the zoom slider's position.
    def update_button_pos(self, x: int, y: int) -> None:
        """
        Updates the position of the zoom slider UI.

        Args:
            x: The new x-coordinate.
            y: The new y-coordinate.
        """
        self.rect.topleft = (x, y)
        self.slider.update_pos(x, y)

    # Draws the zoom slider and percentage text.
    def draw(self, screen: pygame.Surface, context: Dict[str, Any]) -> None:
        """
        Draws the zoom slider UI (slider and text).

        Args:
            screen: The pygame.Surface to draw on.
            context: The shared canvas context.
        """
        self.slider.draw(screen)
        
        # Draw the zoom percentage text
        zoom_text: str = f"{int(context['zoom_level'] * 100)}%"
        zoom_surf: pygame.Surface = self.font.render(zoom_text, True, (255, 255, 255))
        zoom_rect: pygame.Rect = zoom_surf.get_rect(midleft=(self.slider.rect.right + 10, self.slider.rect.centery))
        screen.blit(zoom_surf, zoom_rect)