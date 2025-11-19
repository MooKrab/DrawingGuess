import pygame
from typing import Optional, Tuple, Any

# Defines an Input UI component (text box).
class Input:
    """
    A simple text input box UI component.
    Handles text entry, backspace, and cursor blinking.
    Can be configured for numeric-only or alphanumeric input.
    """
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str = '', font: Optional[pygame.font.Font] = None, 
                 bg_color: Any = (255, 255, 255), text_color: Any = (0, 0, 0), 
                 active_color: Any = (200, 200, 255), border_color: Any = (100, 100, 100),
                 numeric_only: bool = True):
        """
        Initializes the Input box.

        Args:
            x: The x-coordinate of the top-left corner.
            y: The y-coordinate of the top-left corner.
            width: The width of the input box.
            height: The height of the input box.
            text: The initial text in the box.
            font: The pygame.font.Font to use. Defaults to None (size 28).
            bg_color: The background color when inactive.
            text_color: The color of the text and cursor.
            active_color: The background color when active (clicked on).
            border_color: The color of the box's border.
            numeric_only: If True, only allows digits. If False, allows text.
        """
        
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)
        self.text: str = text
        self.font: pygame.font.Font = font if font else pygame.font.Font(None, 28)
        
        self.bg_color: Any = bg_color
        self.text_color: Any = text_color
        self.active_color: Any = active_color
        self.border_color: Any = border_color
        self.numeric_only: bool = numeric_only
        
        self.active: bool = False # True if the user clicked on the box
        self.text_surface: pygame.Surface = self.font.render(text, True, self.text_color)
        
        # --- Cursor Blink Logic ---
        self.cursor_visible: bool = True
        self.cursor_timer: int = 0
        self.CURSOR_BLINK_RATE: int = 500 # milliseconds

    # Sets the text programmatically.
    def set_text(self, text: Any) -> None:
        """
        Updates the text in the input box and re-renders the text surface.

        Args:
            text: The new text to set (will be converted to a string).
        """
        self.text = str(text)
        self.text_surface = self.font.render(self.text, True, self.text_color)

    # Gets the current text.
    def get_text(self) -> str:
        """
        Returns the current text string in the input box.

        Returns:
            The text string.
        """
        return self.text

    # Handles user input events for the text box.
    def handle_event(self, event: pygame.event.Event) -> Tuple[bool, str]:
        """
        Processes pygame events for clicking, typing, and pressing Enter.

        Args:
            event: The pygame.event.Event to process.

        Returns:
            A tuple (value_changed, current_text):
            - value_changed (bool): True if Enter was pressed.
            - current_text (str): The current text in the box.
        """
        value_changed: bool = False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Toggle active state based on click position
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            # Reset cursor blink on click
            self.cursor_timer = pygame.time.get_ticks()
            self.cursor_visible = True
                
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
                value_changed = True # Signal that user confirmed input
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Filter input based on configuration
                if self.numeric_only:
                    if event.unicode.isdigit():
                        self.text += event.unicode
                else:
                    # Allow generic text input (filtering control chars)
                    if len(event.unicode) > 0 and event.unicode.isprintable():
                        self.text += event.unicode
            
            # Re-render text surface and reset cursor
            self.text_surface = self.font.render(self.text, True, self.text_color)
            self.cursor_timer = pygame.time.get_ticks()
            self.cursor_visible = True

        return value_changed, self.text

    # Updates the input box's position.
    def update_pos(self, x: int, y: int) -> None:
        """
        Updates the top-left position of the input box.

        Args:
            x: The new x-coordinate.
            y: The new y-coordinate.
        """
        self.rect.topleft = (x, y)

    # Draws the input box on the screen.
    def draw(self, screen: pygame.Surface) -> None:
        """
        Draws the input box, text, and cursor (if active)
        on the provided surface.

        Args:
            screen: The pygame.Surface to draw on.
        """
        # Set background color based on active state
        current_bg: Any = self.active_color if self.active else self.bg_color
        pygame.draw.rect(screen, current_bg, self.rect)
        
        # Draw border
        pygame.draw.rect(screen, self.border_color, self.rect, 2)
        
        # Center text vertically, add left padding
        text_rect: pygame.Rect = self.text_surface.get_rect(midleft=(self.rect.x + 5, self.rect.centery))
        
        # --- Clipping to keep text inside the box ---
        clipping_rect: pygame.Rect = self.rect.inflate(-4, -4) # Padding
        old_clip: Optional[pygame.Rect] = screen.get_clip()
        screen.set_clip(clipping_rect)
        
        screen.blit(self.text_surface, text_rect)
        
        # --- Draw Cursor ---
        if self.active:
            # Update cursor visibility based on blink rate
            now: int = pygame.time.get_ticks()
            if now - self.cursor_timer > self.CURSOR_BLINK_RATE:
                self.cursor_timer = now
                self.cursor_visible = not self.cursor_visible
            
            if self.cursor_visible:
                # Position cursor at the end of the text
                cursor_x: int = text_rect.right + 2
                
                # Ensure cursor draws even if text is empty
                if len(self.text) == 0:
                    cursor_x = self.rect.x + 5

                pygame.draw.line(screen, self.text_color, 
                                 (cursor_x, self.rect.top + 5), 
                                 (cursor_x, self.rect.bottom - 5), 2)
        
        screen.set_clip(old_clip)