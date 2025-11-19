import sys
import pygame
from typing import Any, List, Tuple, Dict

# Data structure for the scrolling credits.
# Format:
# (Text, Font Size, "center")
# (Text Left, Text Right, Font Size, "columns")
# ("", Size, "spacer")
CREDITS_DATA: List[Tuple[Any, ...]] = [
    ("DrawingGuess", 60, "center"),
    ("", 30, "spacer"),

    ("A Game By", 40, "center"),
    ("ABC Team", 50, "center"),
    ("", 60, "spacer"),

    ("Programmer", 40, "center"),
    ("Suphakorn Khamwongsa", "@notplai", 30, "columns"),
    ("", 30, "spacer"),

    ("Artists", 40, "center"),
    ("Sorawit Nuamwat", "@sorwit_ball", 30, "columns"),
    ("", 30, "spacer"),

    ("Designer", 40, "center"),
    ("Suphakorn Khamwongsa", "Sorawit Nuamwat", 30, "columns"),
    ("", 30, "spacer"),

    ("Tester", 40, "center"),
    ("Sorawit Nuamwat", "", 30, "columns"),
    ("", 30, "spacer"),

    ("Special Thanks", 40, "center"),
    ("Coffee", "Iced Green Tea", 30, "columns"),
    ("Taiwan Milk Tea", "Iced Matcha Latte", 30, "columns"),
    ("UCompiler", "Google Gemini 3", 30, "columns"),
    ("Pygame CE", "Stack Overflow", 30, "columns"),
    ("", 60, "spacer"),

    # Spacers to push "Thanks for playing!" off-screen
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    ("", 60, "spacer"),
    
    ("Thanks for playing!", 80, "center"),
    ("", 60, "spacer"),
]

# Defines the Credits surface (scrolling credits).
def surface(screen: pygame.Surface, background: pygame.Surface) -> None:
    """
    Runs the main loop for the scrolling Credits screen.
    Scrolls the CREDITS_DATA text up the screen.

    Args:
        screen: The main pygame display surface.
        background: The background image surface.
    """
    running: bool = True
    clock: pygame.time.Clock = pygame.time.Clock()
    
    screen_width: int = screen.get_width()
    screen_height: int = screen.get_height()

    overlay: pygame.Surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180)) # Darker overlay for credits
    
    # --- Pre-render all text surfaces ---
    center_x: float = screen_width / 2
    column_1_x: float = center_x - 50 # Right-aligned
    column_2_x: float = center_x + 50 # Left-aligned
    
    rendered_texts: List[Tuple[pygame.Surface, pygame.Rect]] = []
    current_y: float = screen_height + 50 # Start below the screen
    
    fonts: Dict[int, pygame.font.Font] = {} # Cache fonts by size
    
    for row in CREDITS_DATA:
        size: int = row[1] if len(row) == 3 else row[2]
        
        # Load font if not already cached
        if size not in fonts:
            try:
                fonts[size] = pygame.font.Font("freesansbold.ttf", size)
            except FileNotFoundError:
                fonts[size] = pygame.font.Font(None, size)
        font: pygame.font.Font = fonts[size]
        
        row_type: str = row[-1]

        if row_type == 'center':
            text: str = row[0]
            if text:
                text_surf: pygame.Surface = font.render(text, True, "White")
                text_rect: pygame.Rect = text_surf.get_rect(center=(center_x, current_y))
                rendered_texts.append((text_surf, text_rect))
        
        elif row_type == 'columns':
            text_left: str = row[0]
            text_right: str = row[1]
            
            if text_left:
                surf_left: pygame.Surface = font.render(text_left, True, "White")
                rect_left: pygame.Rect = surf_left.get_rect(topright=(column_1_x, current_y))
                rendered_texts.append((surf_left, rect_left))
            
            if text_right:
                surf_right: pygame.Surface = font.render(text_right, True, "White")
                rect_right: pygame.Rect = surf_right.get_rect(topleft=(column_2_x, current_y))
                rendered_texts.append((surf_right, rect_right))
        
        # Move Y-position down for the next row
        current_y += size + 10
    # --- End Pre-rendering ---
        
    # Get the rect for the final "Thanks" message to know when to stop
    thanks_rect: pygame.Rect = rendered_texts[-1][1] if rendered_texts else pygame.Rect(0,0,0,0)
    
    scroll_y: float = 0
    scroll_speed: float = 1.5
    scrolling_stopped: bool = False
    
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False # Exit credits
        
        # --- Update Scroll ---
        if not scrolling_stopped:
            scroll_y += scroll_speed
            
            # Check if the "Thanks" message has reached the center
            if thanks_rect:
                current_thanks_y: float = thanks_rect.centery - scroll_y
                if current_thanks_y <= screen_height / 2:
                    scrolling_stopped = True
                    # Lock the scroll position
                    scroll_y = thanks_rect.centery - (screen_height / 2)

        # --- Drawing ---
        screen.blit(background, (0, 0))
        screen.blit(overlay, (0, 0))
        
        # Draw all pre-rendered text, offset by the current scroll_y
        for surf, rect in rendered_texts:
            draw_rect: pygame.Rect = rect.move(0, -scroll_y)
            # Only blit if it's on the screen (basic culling)
            if draw_rect.bottom > 0 and draw_rect.top < screen_height:
                screen.blit(surf, draw_rect)

        pygame.display.flip()
        clock.tick(60)