import sys
import pygame
from typing import Any, Dict, Callable, Optional
from libs.utils.configs import loadsConfig, savesConfig
from libs.common.components import SolidButton, SolidBox, SolidDropDown, ImageButton
from libs.utils.pylog import Logger
from libs.utils.music import get_music_manager

logger = Logger(__name__)

# Defines the Settings surface (screen).
def surface(screen: pygame.Surface, background: pygame.Surface, 
            load_background_image_func: Callable[[str], pygame.Surface]) -> Dict[str, Any]:
    """
    Runs the main loop for the Settings screen.
    Allows changing theme, toggling music, and resetting to defaults.

    Args:
        screen: The main pygame display surface.
        background: The background image surface (will be modified if theme changes).
        load_background_image_func: A function (like `libs.common.kits.resources`)
                                    that takes a theme name and returns a new
                                    background surface.

    Returns:
        The updated settings dictionary.
    """
                
    settings: Dict[str, Any] = loadsConfig()
    running: bool = True
    clock: pygame.time.Clock = pygame.time.Clock()

    # --- Initialize UI Components ---
    back_btn: ImageButton = ImageButton(
        x=50, y=50,
        image_name="back",
        theme=settings['themes'],
        default_width=150,
        default_height=80
    )
    
    themes_dropdown: SolidDropDown = SolidDropDown(
        x=screen.get_width() / 2 - 150, y=300, 
        width=335, height=50,
        main_text="Theme",
        options=["CuteChaos", "StarSketch", "BubblePencil"]
    )
    themes_dropdown.set_selected(settings['themes'])
    
    music_checkbox: SolidBox = SolidBox(
        x=screen.get_width() / 2 - 150, y=400,
        width=50, height=50,
        label="Music",
        initial_checked=settings['music']
    )
    
    default_btn: SolidButton = SolidButton(
        x=screen.get_width() / 2 - 150, y=500,
        width=300, height=50,
        text="Reset Default",
        font_size=30
    )

    overlay: pygame.Surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150)) # Semi-transparent overlay

    font_title: pygame.font.Font
    try:
        font_title = pygame.font.Font("freesansbold.ttf", 80)
    except FileNotFoundError:
        font_title = pygame.font.Font(None, 80)
    title_surf: pygame.Surface = font_title.render("Settings", True, "White")
    title_rect: pygame.Rect = title_surf.get_rect(center=(screen.get_width()/2, 100))
    # --- End UI Initialization ---
    
    while running:
        # Check if dropdown was open *before* processing events
        # This helps consume clicks that close the dropdown
        dropdown_was_open: bool = themes_dropdown.is_open

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Event: Click Back button or press Escape
            if back_btn.is_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                savesConfig(settings) # Save settings on exit
                running = False
                continue 

            # Event: Interact with Theme dropdown
            new_theme: Optional[str] = themes_dropdown.handle_event(event)
            if new_theme:
                settings['themes'] = new_theme
                
                # Reload background and back button for new theme
                background = load_background_image_func(new_theme)
                back_btn.reload_image(new_theme)
                
                continue # Event handled

            # If dropdown was open and we get a mouse click, it was probably
            # the click that closed the dropdown. Consume it.
            if dropdown_was_open and event.type == pygame.MOUSEBUTTONDOWN:
                continue 

            # Event: Click Reset Default button
            if default_btn.is_clicked(event):
                settings = {"themes": "BubblePencil", "music": True}
                
                # Update UI to match new default settings
                themes_dropdown.set_selected(settings['themes'])
                music_checkbox.checked = settings['music']
                background = load_background_image_func(settings['themes'])
                back_btn.reload_image(settings['themes'])
                
                # --- NEW: Apply music default immediately ---
                get_music_manager().update(settings['music'])
                
                continue 

            # Event: Click Music checkbox
            if music_checkbox.handle_event(event):
                settings['music'] = music_checkbox.checked
                
                # [MISSING LINE] Update the music manager immediately
                get_music_manager().update(settings['music'])
                
                continue # Event handled

        # --- Drawing ---
        screen.blit(background, (0, 0))
        screen.blit(overlay, (0, 0))

        screen.blit(title_surf, title_rect)

        # Draw UI components
        back_btn.draw(screen)
        music_checkbox.draw(screen)
        default_btn.draw(screen)
        themes_dropdown.draw(screen) # Draw dropdown last so it appears on top

        pygame.display.flip()
        
        clock.tick(60)
        
    return settings # Return updated settings to main loop