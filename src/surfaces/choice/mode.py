import sys
import pygame
from typing import Any, Dict
from libs.common.components import SolidButton, ImageButton
from ..projects import canvasSurface, quickSurface
from libs.utils.configs import loadsConfig
from libs.utils.pylog import Logger

logger = Logger(__name__)

# Defines the Mode Selection surface.
def surface(screen: pygame.Surface, background: pygame.Surface) -> None:
    """
    Runs the main loop for the Mode/File selection screen.
    This surface acts as a two-part menu:
    1. ("mode")   Select "FreeInk" (canvas) or "Guessing" (not implemented).
    2. ("file")   Select "New Canva" or "Open from File".

    Args:
        screen: The main pygame display surface.
        background: The background image surface.
    """
    settings: Dict[str, Any] = loadsConfig()
    running: bool = True
    clock: pygame.time.Clock = pygame.time.Clock()
    
    current_view: str = "mode" # State machine: "mode" or "file"

    overlay: pygame.Surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150)) # Semi-transparent overlay
    
    # --- Fonts and Titles ---
    font_title: pygame.font.Font
    font_subtitle: pygame.font.Font
    try:
        font_title = pygame.font.Font("freesansbold.ttf", 80)
        font_subtitle = pygame.font.Font("freesansbold.ttf", 50)
    except FileNotFoundError:
        font_title = pygame.font.Font(None, 80)
        font_subtitle = pygame.font.Font(None, 50)
        
    title_surf: pygame.Surface = font_title.render("Select Mode", True, "White")
    title_rect: pygame.Rect = title_surf.get_rect(center=(screen.get_width()/2, 100))
    
    file_title_surf: pygame.Surface = font_title.render("Open", True, "White")
    file_title_rect: pygame.Rect = file_title_surf.get_rect(center=(screen.get_width()/2, 100))

    # --- UI Components ---
    btn_width: int = 400
    btn_height: int = 80
    btn_x: float = (screen.get_width() - btn_width) / 2
    
    # "Mode" view buttons
    freeink_btn: SolidButton = SolidButton(
        x=btn_x, y=250, width=btn_width, height=btn_height,
        text="FreeInk", font_size=50
    )
    
    quick_btn: SolidButton = SolidButton(
        x=btn_x, y=350, width=btn_width, height=btn_height,
        text="QuickInk", font_size=50
    )
    
    ai_btn: SolidButton = SolidButton(
        x=btn_x, y=450, width=btn_width, height=btn_height,
        text="AI Lookup", text_color=(150, 150, 150),
        bg_color=(50, 50, 50), border_color=(100, 100, 100), font_size=50
    )
    
    back_btn: ImageButton = ImageButton(
        x=50, y=50,
        image_name="back",
        theme=settings['themes'],
        default_width=150,
        default_height=80
    )

    # "File" view buttons
    new_whiteboard_btn: SolidButton = SolidButton(
        x=btn_x, y=250, width=btn_width, height=btn_height,
        text="New Canva", font_size=50
    )
    
    open_file_btn: SolidButton = SolidButton(
        x=btn_x, y=350, width=btn_width, height=btn_height,
        text="Open from File", font_size=50
    )
    
    back_file_btn: SolidButton = SolidButton(
        x=btn_x, y=450, width=btn_width, height=btn_height,
        text="Back", font_size=50
    )
    # --- End UI Components ---

    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if current_view == "mode":
                # --- Mode View Events ---
                if back_btn.is_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False # Go back to main menu
                
                if freeink_btn.is_clicked(event):
                    current_view = "file" # Go to file menu
                
                if quick_btn.is_clicked(event):
                    quickSurface(screen, background, False)
                
            elif current_view == "file":
                # --- File View Events ---
                if new_whiteboard_btn.is_clicked(event):
                    logger.info("Opening new whiteboard...")
                    # Launch canvas with a new, blank whiteboard
                    canvasSurface(screen, background, False)
                
                if open_file_btn.is_clicked(event):
                    logger.info("Opening whiteboard with file dialog...")
                    # Launch canvas and trigger the "open file" dialog
                    canvasSurface(screen, background, True)
                
                if back_file_btn.is_clicked(event):
                    current_view = "mode" # Go back to mode menu

        # --- Drawing ---
        screen.blit(background, (0, 0))
        screen.blit(overlay, (0, 0))
        
        if current_view == "mode":
            # Draw "Mode" view
            screen.blit(title_surf, title_rect)
            back_btn.draw(screen)
            freeink_btn.draw(screen)
            quick_btn.draw(screen)
            ai_btn.draw(screen)
            
        elif current_view == "file":
            # Draw "File" view
            screen.blit(file_title_surf, file_title_rect)
            new_whiteboard_btn.draw(screen)
            open_file_btn.draw(screen)
            back_file_btn.draw(screen)

        pygame.display.flip()
        clock.tick(60)