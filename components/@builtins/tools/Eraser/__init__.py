import pygame
from libs.common.components import SolidButton, SolidSlider, InputBox
from typing import Any, Dict, Optional, Tuple

# Defines the EraserTool for erasing on the canvas.
class EraserTool:
    """
    A tool for erasing content on the drawing surface.
    It provides a slider and input box to control the eraser size.
    """
    
    def __init__(self, rect: pygame.Rect, config: Dict[str, Any]):
        """
        Initializes the EraserTool.

        Args:
            rect: The pygame.Rect defining the button's position and size.
            config: The configuration dictionary for this tool, containing name,
                    registryId, type, and icon path.
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
        self.is_drawing_tool: bool = True
        self.last_pos: Optional[Tuple[int, int]] = None  # Stores the last mouse position for smooth drawing

        # --- Popup Modal for Size Control ---
        self.modal_rect: pygame.Rect = pygame.Rect(0, 0, 280, 80)
        self.slider: SolidSlider = SolidSlider(
            x=self.modal_rect.x + 20, y=self.modal_rect.y + 25, 
            width=100, height=30, 
            min_val=1, max_val=40, initial_val=50
        )
        self.input_box: InputBox = InputBox(
            x=self.modal_rect.x + 180, y=self.modal_rect.y + 25,
            width=70, height=30, text='50'
        )
        self.font: pygame.font.Font
        try:
            self.font = pygame.font.Font("freesansbold.ttf", 20)
        except:
            self.font = pygame.font.Font(None, 24)
            
        self.px_label_surf: pygame.Surface = self.font.render("px", True, (0,0,0))
        self.px_label_rect: pygame.Rect = self.px_label_surf.get_rect(center=self.modal_rect.center)
    
    # Returns information for drawing the eraser cursor.
    def get_cursor_draw_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides information for drawing the cursor, which is a white circle
        representing the eraser size.

        Args:
            context: The shared canvas context.

        Returns:
            A dictionary specifying the cursor type, radius, and color.
        """
        return {
            "type": "circle", 
            "radius": context.get("eraser_size", 50) // 2, 
            "color": (255, 255, 255) # Eraser cursor is white
        }

    # Handles user input events for the EraserTool.
    def handle_event(self, event: pygame.event.Event, context: Dict[str, Any]) -> bool:
        """
        Processes pygame events for drawing or interacting with the size modal.

        Args:
            event: The pygame.event.Event to process.
            context: The shared canvas context for updating tool state and drawing.

        Returns:
            True if the event was handled by this tool, False otherwise.
        """
        menu_open: Optional[str] = context.get("menu_open")
        mouse_pos: Tuple[int, int] = context.get("mouse_pos")

        # Event: Click on the tool's button in the toolbar.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == True:
            if self.button.rect.collidepoint(event.pos):
                context["active_tool_id"] = self.registryId
                
                # Toggle the size modal
                if context.get("menu_open") == self.registryId:
                    context["menu_open"] = None
                else:
                    context["menu_open"] = self.registryId
                    # Sync modal with current eraser size
                    current_size: int = context.get("eraser_size", 50)
                    self.slider.set_value(current_size)
                    self.input_box.set_text(str(current_size))
                return True # Event handled

        # If the size modal is not open, handle drawing events.
        if menu_open != self.registryId:
            return self._handle_drawing_events(event, context)

        # --- Logic for when the size modal is open ---
        self._update_popup_rects(context) # Update modal position

        # Event: Interact with the size slider.
        if self.slider.handle_event(event):
            new_size: int = int(self.slider.get_value())
            context["eraser_size"] = new_size
            self.input_box.set_text(str(new_size)) # Sync input box
            return True # Event handled
            
        # Event: Interact with the size input box.
        input_changed: bool
        new_text: str
        input_changed, new_text = self.input_box.handle_event(event)
        if input_changed:
            new_size_input: int
            try:
                new_size_input = int(new_text)
                new_size = max(1, min(new_size_input, 2048)) # Clamp size
            except ValueError:
                new_size = context.get("eraser_size", 50) # Reset on invalid input
            
            context["eraser_size"] = new_size
            self.slider.set_value(new_size) # Sync slider
            self.input_box.set_text(str(new_size))
            return True # Event handled
        elif self.input_box.active:
             return True # Event handled (typing in box)

        # Event: Click inside the modal (consume the click).
        if event.type == pygame.MOUSEBUTTONDOWN and self.modal_rect.collidepoint(mouse_pos):
             return True
             
        # Event: Click outside the modal (close it).
        if event.type == pygame.MOUSEBUTTONDOWN and not self.modal_rect.collidepoint(mouse_pos):
            context["menu_open"] = None
            return False # Let the drawing handler process this click if it's on the canvas
            
        # Event: Mouse is over the modal (consume it).
        if self.modal_rect.collidepoint(mouse_pos):
            return True

        # Fallback to drawing events if no modal interaction occurred.
        return self._handle_drawing_events(event, context)

    # Handles the actual drawing (erasing) logic.
    def _handle_drawing_events(self, event: pygame.event.Event, context: Dict[str, Any]) -> bool:
        """
        Private method to process drawing events (mouse down, move, up) on the canvas.

        Args:
            event: The pygame.event.Event to process.
            context: The shared canvas context.

        Returns:
            True if a drawing event was handled, False otherwise.
        """
        if context.get("active_tool_id") != self.registryId: 
            return False
        
        canvas_mouse_pos: Tuple[int, int] = context.get("canvas_mouse_pos", context.get("mouse_pos"))
        
        # Event: Start erasing (mouse button down on canvas).
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not context["click_on_ui"]:
                self.last_pos = canvas_mouse_pos
                context["is_drawing"] = True
                
                drawing_surface: pygame.Surface = context["drawing_surface"]
                eraser_size: int = context.get("eraser_size", 50)
                # Draw a circle at the start point
                pygame.draw.circle(drawing_surface, "White", self.last_pos, max(1, eraser_size // 2))
                
                return True # Event handled

        # Event: Stop erasing (mouse button up).
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if context["is_drawing"]:
                context["is_drawing"] = False
                if self.last_pos:
                    # Add this stroke to the history
                    context["add_history"](f"{self.name} Stroke")
                self.last_pos = None
                return True # Event handled

        # Event: Erase (mouse motion while button is down).
        elif event.type == pygame.MOUSEMOTION:
            if context["is_drawing"] and self.last_pos:
                drawing_surface: pygame.Surface = context["drawing_surface"]
                eraser_size: int = context.get("eraser_size", 50)
                current_pos: Tuple[int, int] = canvas_mouse_pos
                
                # Draw circles and lines for a continuous stroke
                pygame.draw.circle(drawing_surface, "White", self.last_pos, max(1, eraser_size // 2))
                pygame.draw.circle(drawing_surface, "White", current_pos, max(1, eraser_size // 2))
                pygame.draw.line(drawing_surface, "White", self.last_pos, current_pos, max(1, eraser_size))

                self.last_pos = current_pos
                return True # Event handled
        
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

    # Updates the position of the size modal popup.
    def _update_popup_rects(self, context: Dict[str, Any]) -> None:
        """
        Private method to update the position of the size modal relative
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
        
        # Update positions of slider, input box, and label relative to the modal
        self.slider.update_pos(self.modal_rect.x + 20, self.modal_rect.y + 25)
        
        input_x: int = self.slider.rect.right + 10
        self.input_box.update_pos(input_x, self.slider.rect.y)
        
        self.px_label_rect.midleft = (self.input_box.rect.right + 5, self.input_box.rect.centery)

    # Draws the EraserTool button and its size modal if open.
    def draw(self, screen: pygame.Surface, context: Dict[str, Any]) -> None:
        """
        Draws the tool's button and the size modal (if active).

        Args:
            screen: The pygame.Surface to draw on.
            context: The shared canvas context.
        """
        menu_open: Optional[str] = context.get("menu_open")
        is_active: bool = context.get("active_tool_id") == self.registryId 
        
        if is_active:
            # Draw highlight if active
            pygame.draw.rect(screen, (200, 200, 0), self.button.rect.inflate(4, 4))
        
        self.button.draw(screen) 
        
        # Draw the size modal if this tool's menu is open
        if menu_open == self.registryId:
            self._update_popup_rects(context)
            
            pygame.draw.rect(screen, (220, 220, 220), self.modal_rect)
            pygame.draw.rect(screen, (0,0,0), self.modal_rect, 2)
            
            self.slider.draw(screen)
            self.input_box.draw(screen)
            screen.blit(self.px_label_surf, self.px_label_rect)