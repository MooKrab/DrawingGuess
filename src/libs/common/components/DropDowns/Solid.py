import pygame
from typing import List, Tuple, Optional, Any

# Defines a Dropdown UI component.
class Dropdown:
    """
    A simple dropdown menu UI component.
    Shows a main bar and a list of options when clicked.
    Supports scrolling if there are many options.
    """
    
    def __init__(self, x: int, y: int, width: int, height: int, main_text: str, options: List[str], 
                 font_size: int = 30, text_color: Any = 'White', bg_color: Any = (100, 100, 100), 
                 option_bg_color: Any = (200, 200, 200), option_text_color: Any = 'Black',
                 max_visible_options: int = 5):
        """
        Initializes the Dropdown.

        Args:
            x: The x-coordinate of the top-left corner.
            y: The y-coordinate of the top-left corner.
            width: The width of the dropdown bar and options.
            height: The height of the main bar and each option.
            main_text: The placeholder text (e.g., "Select Category").
            options: A list of string options for the dropdown.
            font_size: The font size for all text.
            text_color: The color of the text on the main bar.
            bg_color: The background color of the main bar.
            option_bg_color: The background color of the option boxes.
            option_text_color: The color of the text for the options.
            max_visible_options: Maximum number of options to show at once (requires scrolling for more).
        """
        
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)
        self.main_text: str = main_text
        self.options: List[str] = options
        self.selected_option: str = ""
        
        self.is_open: bool = False # True if the options are visible
        
        self.text_color: Any = text_color
        self.bg_color: Any = bg_color
        self.option_bg_color: Any = option_bg_color
        self.option_text_color: Any = option_text_color
        
        # Scrolling state
        self.max_visible_options: int = max_visible_options
        self.scroll_offset: int = 0
        
        self.font: pygame.font.Font
        try:
            self.font = pygame.font.Font("freesansbold.ttf", font_size)
        except FileNotFoundError:
            self.font = pygame.font.Font(None, font_size)

        # Pre-render surfaces for each option to optimize drawing
        self.option_surfs: List[pygame.Surface] = [
            self.font.render(option, True, self.option_text_color) 
            for option in self.options
        ]

        # Surfaces for the main display bar
        self.current_display_surf: Optional[pygame.Surface] = None
        self.current_display_rect: Optional[pygame.Rect] = None
        self._update_main_display()

    def _update_main_display(self) -> None:
        """Updates the rendered surface for the main text area."""
        # Display selected option if one exists, otherwise show the placeholder (main_text)
        full_text: str = self.selected_option if self.selected_option else self.main_text
        
        self.current_display_surf = self.font.render(full_text, True, self.text_color)
        self.current_display_rect = self.current_display_surf.get_rect(
            midleft=(self.rect.x + 10, self.rect.centery)
        )

    # Sets the currently selected option.
    def set_selected(self, option: str) -> None:
        """
        Sets the selected option and updates the main display text.

        Args:
            option: The string of the option to select.
        """
        self.selected_option = option
        self._update_main_display()

    # Handles user input events for the dropdown.
    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        Processes pygame events for opening, closing, selecting options, and scrolling.
        
        Behavior Update:
        - Clicking the header toggles open/close.
        - Selecting an option DOES NOT close the dropdown (keeps it open).
        - Clicking outside DOES NOT close the dropdown (must click header to close).

        Args:
            event: The pygame.event.Event to process.

        Returns:
            The string of the newly selected option if one was chosen,
            otherwise None.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # Click on the main bar: toggle open/closed
            if self.rect.collidepoint(mouse_pos):
                self.is_open = not self.is_open
                return None
            
            # Click while open: check if a visible option was clicked
            if self.is_open:
                visible_count = min(len(self.options), self.max_visible_options)
                dropdown_height = visible_count * self.rect.height
                dropdown_area = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.width, dropdown_height)
                
                if dropdown_area.collidepoint(mouse_pos):
                    # Calculate which index was clicked based on Y position
                    relative_y = mouse_pos[1] - self.rect.bottom
                    clicked_visual_index = int(relative_y // self.rect.height)
                    
                    actual_index = self.scroll_offset + clicked_visual_index
                    
                    if 0 <= actual_index < len(self.options):
                        new_option: str = self.options[actual_index]
                        self.set_selected(new_option)
                        # self.is_open = False # <--- REMOVED: Keep open after selection
                        return new_option 
            
            # Click outside logic removed to satisfy "must still appear until user click header"
            # self.is_open = False 
            
        elif event.type == pygame.MOUSEWHEEL and self.is_open:
            # Check if mouse is hovering over the dropdown area to allow scrolling
            mouse_pos = pygame.mouse.get_pos()
            visible_count = min(len(self.options), self.max_visible_options)
            total_height = self.rect.height + (visible_count * self.rect.height)
            # Include main rect in hover area for UX
            full_area = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, total_height)
            
            if full_area.collidepoint(mouse_pos):
                if event.y > 0: # Scroll UP
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                elif event.y < 0: # Scroll DOWN
                    max_offset = max(0, len(self.options) - self.max_visible_options)
                    self.scroll_offset = min(max_offset, self.scroll_offset + 1)

        return None

    # Draws the dropdown on the screen.
    def draw(self, screen: pygame.Surface) -> None:
        """
        Draws the main dropdown bar and the option list (if open).

        Args:
            screen: The pygame.Surface to draw on.
        """
        # Draw the main bar
        pygame.draw.rect(screen, self.bg_color, self.rect)
        pygame.draw.rect(screen, self.text_color, self.rect, 2)
        
        if self.current_display_surf and self.current_display_rect:
            # Clip text if it's too long
            screen.set_clip(self.rect.inflate(-10, -10))
            screen.blit(self.current_display_surf, self.current_display_rect)
            screen.set_clip(None)

        # Draw the options list if open
        if self.is_open:
            visible_count = min(len(self.options), self.max_visible_options)
            
            for i in range(visible_count):
                option_index = self.scroll_offset + i
                if option_index >= len(self.options):
                    break
                
                # Calculate position for this specific row
                y_pos = self.rect.bottom + (i * self.rect.height)
                option_rect = pygame.Rect(self.rect.x, y_pos, self.rect.width, self.rect.height)
                
                # Draw background and border
                pygame.draw.rect(screen, self.option_bg_color, option_rect)
                pygame.draw.rect(screen, 'Black', option_rect, 1)
                
                # Blit the pre-rendered option text
                surf = self.option_surfs[option_index]
                surf_rect = surf.get_rect(midleft=(option_rect.x + 10, option_rect.centery))
                
                # Clip option text if too long
                screen.set_clip(option_rect.inflate(-10, -10))
                screen.blit(surf, surf_rect)
                screen.set_clip(None)
            
            # Draw scrollbar indicator if needed
            if len(self.options) > self.max_visible_options:
                total_dropdown_height = visible_count * self.rect.height
                scrollbar_width = 5
                scrollbar_bg_rect = pygame.Rect(self.rect.right - scrollbar_width - 2, self.rect.bottom, scrollbar_width, total_dropdown_height)
                
                # Calculate thumb size and position
                view_ratio = self.max_visible_options / len(self.options)
                thumb_height = max(20, total_dropdown_height * view_ratio)
                max_scroll = len(self.options) - self.max_visible_options
                scroll_ratio = self.scroll_offset / max_scroll if max_scroll > 0 else 0
                thumb_y = scrollbar_bg_rect.y + (total_dropdown_height - thumb_height) * scroll_ratio
                
                thumb_rect = pygame.Rect(scrollbar_bg_rect.x, thumb_y, scrollbar_width, thumb_height)
                
                pygame.draw.rect(screen, (150, 150, 150), scrollbar_bg_rect)
                pygame.draw.rect(screen, (50, 50, 50), thumb_rect)