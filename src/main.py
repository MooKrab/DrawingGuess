"""
DrawingGuess Main Application
This script initializes pygame and runs the main menu loop.
It handles:
- Displaying the main menu buttons (Play, Settings, Exit).
- Switching between different themes and layouts.
- Launching other surfaces (Settings, Credits, Mode Selection).
- The quit confirmation dialog.
"""

import os
import sys
import pygame
import random
from typing import Any, Dict, List, Tuple, Optional
# Import surfaces (screens) to navigate to
from surfaces import SettingsSurface, CreditsSurface, SelSurface
from libs.common.components import ImageButton
from libs.utils.configs import loadsConfig
from libs.common.kits import resources
from libs.utils.pylog import Logger
from libs.utils.music import get_music_manager

logger = Logger(__name__)

pygame.init()

# --- Screen and Dialog Constants ---
SCREEN_WIDTH: int = 1668
SCREEN_HIGH: int = 938

DIALOG_WIDTH: int = 550
DIALOG_HEIGHT: int = 200
DIALOG_BTN_WIDTH: int = 126
DIALOG_BTN_HEIGHT: int = 77
DIALOG_BTN_GAP: int = 20
DIALOG_CENTER_X: int = SCREEN_WIDTH // 2
DIALOG_CENTER_Y: int = SCREEN_HIGH // 2

screen: pygame.Surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HIGH))
pygame.display.set_caption("DrawingGuess")

# --- BubblePencil Pop Effect Classes ---
class PopEffect:
    def __init__(self, image: pygame.Surface, x: int, y: int):
        # Randomly scale the image (maintain 1:1 aspect ratio as requested)
        scale_factor = random.uniform(0.5, 1.5)
        new_width = int(image.get_width() * scale_factor)
        new_height = int(image.get_height() * scale_factor)
        
        # Scale and copy the image
        self.image = pygame.transform.smoothscale(image, (new_width, new_height)).copy()
        
        self.rect = self.image.get_rect(topleft=(x, y))
        self.alpha = 0.0
        self.state = 0 # 0: Fade In, 1: Hold, 2: Fade Out
        self.timer = 0
        
        # Randomize timing slightly
        self.fade_speed = random.uniform(2, 4)
        self.hold_duration = random.randint(60, 180) # frames (approx 1-3 seconds at 60fps)

    def update(self) -> bool:
        # Returns False if dead (animation finished)
        if self.state == 0: # Fade In
            self.alpha += self.fade_speed
            if self.alpha >= 255:
                self.alpha = 255
                self.state = 1
        elif self.state == 1: # Hold
            self.timer += 1
            if self.timer >= self.hold_duration:
                self.state = 2
        elif self.state == 2: # Fade Out
            self.alpha -= self.fade_speed
            if self.alpha <= 0:
                return False
        
        # Apply alpha
        self.image.set_alpha(int(self.alpha))
        return True

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

class PopManager:
    def __init__(self):
        self.assets: Dict[str, pygame.Surface] = {}
        self.active_pops: List[Dict[str, Any]] = [] # List of dicts: { 'name': str, 'obj': PopEffect }
        self.loaded = False
        # Path adjusted to match project structure: src/assets/textures/environments...
        self.base_path = os.path.abspath('src/assets/textures/environments/.BubblePencil/Extras')

    def load_assets(self):
        if self.loaded: return
        
        if not os.path.exists(self.base_path):
            # Only log once to avoid spam if folder doesn't exist
            # logger.warning(f"BubblePencil Extras path not found: {self.base_path}")
            self.loaded = True 
            return
        
        logger.info(f"Loading BubblePencil extras from: {self.base_path}")
        for filename in os.listdir(self.base_path):
            if filename.startswith("Pop_") and filename.endswith(".png"):
                full_path = os.path.join(self.base_path, filename)
                try:
                    img = pygame.image.load(full_path).convert_alpha()
                    self.assets[filename] = img
                except Exception as e:
                    logger.warning(f"Failed to load pop image {filename}: {e}")
        self.loaded = True

    def update(self, screen_width: int, screen_height: int):
        if not self.assets: return

        # Update active pops and remove dead ones
        alive_pops = []
        for p in self.active_pops:
            if p['obj'].update():
                alive_pops.append(p)
        self.active_pops = alive_pops

        # Attempt to spawn a new pop
        # Chance to spawn: ~1% per frame, max 5 concurrent
        if random.random() < 0.01 and len(self.active_pops) < 5:
            available_names = list(self.assets.keys())
            
            # Ensure we don't spawn the same file if it's already on screen
            active_names = {p['name'] for p in self.active_pops}
            candidates = [n for n in available_names if n not in active_names]
            
            if candidates:
                chosen_name = random.choice(candidates)
                img = self.assets[chosen_name]
                
                # Attempt to find a non-overlapping position (try 10 times)
                for _ in range(10):
                    # Calculate max possible scale to ensure we check bounds correctly
                    # (approximate, assuming max scale is 1.5)
                    max_w = int(img.get_width() * 1.5)
                    max_h = int(img.get_height() * 1.5)
                    
                    max_x = max(0, screen_width - max_w)
                    max_y = max(0, screen_height - max_h)
                    
                    x = random.randint(0, max_x)
                    y = random.randint(0, max_y)
                    
                    # Create a temp rect for collision check
                    # Note: We don't know exact size until PopEffect is created due to random scale,
                    # but we can estimate or create the object and discard if invalid.
                    # For better performance, let's create the object and check.
                    
                    new_pop = PopEffect(img, x, y)
                    
                    # Check collision with existing pops
                    collision = False
                    for p in self.active_pops:
                        # Add some buffer distance
                        if new_pop.rect.inflate(20, 20).colliderect(p['obj'].rect):
                            collision = True
                            break
                    
                    if not collision:
                        self.active_pops.append({'name': chosen_name, 'obj': new_pop})
                        break

    def draw(self, surface: pygame.Surface):
        for p in self.active_pops:
            p['obj'].draw(surface)

# --- Functions ---

# Updates the layout of the main menu buttons based on the current theme.
def update_button_layout(theme: str, play_btn: ImageButton, settings_btn: ImageButton, quit_btn: ImageButton) -> None:
    """
    Rearranges the positions of the main menu buttons based on the selected theme.

    Args:
        theme: The name of the current theme (e.g., 'StarSketch', 'BubblePencil').
        play_btn: The 'Play' ImageButton instance.
        settings_btn: The 'Settings' ImageButton instance.
        quit_btn: The 'Quit' ImageButton instance.
    """
    if theme == 'StarSketch':
        logger.info("Applying 'StarSketch' layout")
        
        play_w, play_h = play_btn.rect.size
        settings_w, settings_h = settings_btn.rect.size
        
        gap: int = 25
        # Center a row containing Play and Settings
        total_row_width: int = play_w + gap + settings_w
        row_start_x: int = (SCREEN_WIDTH - total_row_width) // 2
        row_y: int = (SCREEN_HIGH - play_h) // 2 - 50 + 100
        
        play_btn.set_pos(row_start_x, row_y)
        settings_btn.set_pos(row_start_x + play_w + gap, row_y)
        
        # Center the Quit button below the row
        quit_x: int = (SCREEN_WIDTH - quit_btn.rect.width) // 2
        quit_y: int = row_y + play_h + 35
        quit_btn.set_pos(quit_x, quit_y)

    elif theme == 'BubblePencil':
        logger.info("Applying 'BubblePencil' layout")
        
        play_w, play_h = play_btn.rect.size
        settings_w, settings_h = settings_btn.rect.size
        quit_w, quit_h = quit_btn.rect.size
        
        # Align buttons to the bottom-right
        padding_right: int = 50
        padding_bottom: int = 50
        gap: int = 25
        
        btn_x: int = SCREEN_WIDTH - quit_w - padding_right
        
        quit_btn_y: int = SCREEN_HIGH - quit_h - padding_bottom
        settings_btn_y: int = quit_btn_y - settings_h - gap
        play_btn_y: int = settings_btn_y - play_h - gap
        
        play_btn.set_pos(btn_x, play_btn_y)
        settings_btn.set_pos(btn_x, settings_btn_y)
        quit_btn.set_pos(btn_x, quit_btn_y)

    else: # Default or 'CuteChaos' layout
        logger.info("Applying 'CuteChaos' (default) layout")
        
        # Center-stack the buttons
        btn_x: int = (SCREEN_WIDTH - play_btn.rect.width) // 2
        
        play_btn.set_pos(btn_x, (SCREEN_HIGH - play_btn.rect.height) // 2 - 30)
        settings_btn.set_pos(btn_x, (SCREEN_HIGH - settings_btn.rect.height) // 2 + 75)
        quit_btn.set_pos(btn_x, (SCREEN_HIGH - quit_btn.rect.height) // 2 + 200)

# --- Initialization ---

# Load settings and background
current_settings: dict[str, Any] = loadsConfig()
background: pygame.Surface = resources(current_settings['themes'])

# Initialize and play music based on settings
get_music_manager().update(current_settings['music'])

# Initialize PopManager for BubblePencil effects
pop_manager = PopManager()

# --- Main Menu Buttons ---
btn_x: int = (SCREEN_WIDTH - 250) // 2 # Initial X for default layout

play_btn: ImageButton = ImageButton(
    x=btn_x, y=(SCREEN_HIGH - 80) // 2 - 50,
    image_name="play",
    theme=current_settings['themes'],
    default_width=396,
    default_height=120
)

settings_btn: ImageButton = ImageButton(
    x=btn_x, y=(SCREEN_HIGH - 80) // 2 + 75,
    image_name="settings",
    theme=current_settings['themes'],
    default_width=396,
    default_height=120
)

quit_btn: ImageButton = ImageButton(
    x=btn_x, y=(SCREEN_HIGH - 80) // 2 + 100,
    image_name="exit",
    theme=current_settings['themes'],
    default_width=396,
    default_height=120
)

# Apply the correct layout based on the loaded theme
update_button_layout(current_settings['themes'], play_btn, settings_btn, quit_btn)

# --- Quit Confirmation Dialog ---
dialog_overlay: pygame.Surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HIGH), pygame.SRCALPHA)
dialog_overlay.fill((0, 0, 0, 128)) # Semi-transparent black overlay

dialog_rect: pygame.Rect = pygame.Rect(0, 0, DIALOG_WIDTH, DIALOG_HEIGHT)
dialog_rect.center = (DIALOG_CENTER_X, DIALOG_CENTER_Y)

dialog_font: pygame.font.Font
try:
    dialog_font = pygame.font.Font("freesansbold.ttf", 28)
except FileNotFoundError:
    dialog_font = pygame.font.Font(None, 28)
    
dialog_text_surf: pygame.Surface = dialog_font.render("I'm felt sad, when see you leave... T^T", True, (0, 0, 0))
dialog_text_rect: pygame.Rect = dialog_text_surf.get_rect(center=(DIALOG_CENTER_X, DIALOG_CENTER_Y - 50))

yes_btn: ImageButton = ImageButton(
    x=0, y=0,
    image_name="yes",
    theme=current_settings['themes'],
    default_width=DIALOG_BTN_WIDTH - 20,
    default_height=DIALOG_BTN_HEIGHT - 20
)

no_btn: ImageButton = ImageButton(
    x=0, y=0,
    image_name="no",
    theme=current_settings['themes'],
    default_width=DIALOG_BTN_WIDTH - 20,
    default_height=DIALOG_BTN_HEIGHT - 20
)

# Position dialog buttons
yes_btn_w: int = yes_btn.rect.width
no_btn_w: int = no_btn.rect.width
total_dialog_btn_width: float = yes_btn_w + DIALOG_BTN_GAP + no_btn_w

yes_btn_x: float = DIALOG_CENTER_X - (total_dialog_btn_width / 2)
no_btn_x: float = yes_btn_x + yes_btn_w + DIALOG_BTN_GAP
btn_y: int = DIALOG_CENTER_Y + 25

yes_btn.set_pos(yes_btn_x, btn_y + 2)
no_btn.set_pos(no_btn_x, btn_y)

# Store original centers for the "shaking" effect
yes_btn_original_center: tuple[int, int] = yes_btn.rect.center
no_btn_original_center: tuple[int, int] = no_btn.rect.center

# --- Credits Link ---
credits_font: pygame.font.Font
credits_font_underlined: pygame.font.Font
try:
    credits_font = pygame.font.Font("freesansbold.ttf", 30)
    credits_font_underlined = pygame.font.Font("freesansbold.ttf", 30)
except FileNotFoundError:
    credits_font = pygame.font.Font(None, 30)
    credits_font_underlined = pygame.font.Font(None, 30)

credits_font_underlined.set_underline(True)

credits_text: str = "MooKrab.org"
credits_color: tuple[int, int, int] = (50, 50, 50)
credits_surf_normal: pygame.Surface = credits_font.render(credits_text, True, credits_color)
credits_surf_underlined: pygame.Surface = credits_font_underlined.render(credits_text, True, credits_color)
credits_rect: pygame.Rect = credits_surf_normal.get_rect(bottomleft=(20, SCREEN_HIGH - 15))

# --- Main Game Loop ---
running: bool = True
confirming_quit: bool = False # State flag for the quit dialog
clock: pygame.time.Clock = pygame.time.Clock()

all_image_buttons: list[ImageButton] = [play_btn, settings_btn, quit_btn, yes_btn, no_btn]

while running:
    
    mouse_pos: tuple[int, int] = pygame.mouse.get_pos()

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            confirming_quit = True

        if confirming_quit:
            # --- Quit Dialog Event Handling ---
            if yes_btn.is_clicked(event):
                running = False # Exit main loop
            if no_btn.is_clicked(event):
                confirming_quit = False # Close dialog
        else:
            # --- Main Menu Event Handling ---
            if play_btn.is_clicked(event):
                # Launch the mode selection surface
                SelSurface(screen, background.copy())
                
            if quit_btn.is_clicked(event):
                confirming_quit = True # Open quit dialog
                
            if settings_btn.is_clicked(event):
                # Launch the settings surface
                updated_settings: dict[str, Any] = SettingsSurface(screen, background.copy(), resources)
                
                theme_changed: bool = updated_settings['themes'] != current_settings['themes']
                
                # If theme changed, reload all assets
                if theme_changed:
                    logger.info(f"Theme setting changed to: {updated_settings['themes']}")
                    new_theme: str = updated_settings['themes']
                    
                    background = resources(new_theme)
                    
                    logger.info("Reloading button images...")
                    for btn in all_image_buttons:
                        btn.reload_image(new_theme)
                        
                    # Recalculate dialog button positions (images might have new sizes)
                    yes_btn_w = yes_btn.rect.width
                    no_btn_w = no_btn.rect.width
                    total_dialog_btn_width = yes_btn_w + DIALOG_BTN_GAP + no_btn_w
                    yes_btn_x = DIALOG_CENTER_X - (total_dialog_btn_width / 2)
                    no_btn_x = yes_btn_x + yes_btn_w + DIALOG_BTN_GAP
                    
                    btn_y = DIALOG_CENTER_Y + 25
                    yes_btn.set_pos(yes_btn_x, btn_y - 5)
                    no_btn.set_pos(no_btn_x, btn_y)

                    yes_btn_original_center = yes_btn.rect.center
                    no_btn_original_center = no_btn.rect.center
                    
                    # Apply new layout for main menu
                    update_button_layout(new_theme, play_btn, settings_btn, quit_btn)
                
                current_settings = updated_settings
            
            # Check for credits link click
            if event.type == pygame.MOUSEBUTTONDOWN and credits_rect.collidepoint(event.pos):
                CreditsSurface(screen, background.copy())

    # --- Updates ---
    if current_settings['themes'] == 'BubblePencil' and not confirming_quit:
        pop_manager.load_assets() # Will do nothing if already loaded
        pop_manager.update(SCREEN_WIDTH, SCREEN_HIGH)

    # --- Drawing ---
    screen.blit(background, (0, 0))
    
    # Draw BubblePencil effects (behind buttons)
    if current_settings['themes'] == 'BubblePencil' and not confirming_quit:
        pop_manager.draw(screen)
    
    # Draw main menu buttons
    play_btn.draw(screen)
    settings_btn.draw(screen)
    quit_btn.draw(screen)

    if confirming_quit:
        # --- Draw Quit Dialog ---
        screen.blit(dialog_overlay, (0, 0))
        
        pygame.draw.rect(screen, (200, 200, 200), dialog_rect) # Dialog box
        pygame.draw.rect(screen, 'Black', dialog_rect, 3) # Border

        screen.blit(dialog_text_surf, dialog_text_rect)

        # Reset button positions (in case of shake)
        yes_btn.rect.center = yes_btn_original_center
        no_btn.rect.center = no_btn_original_center
        
        # "Shake" the 'Yes' button on hover
        if yes_btn.rect.collidepoint(mouse_pos):
            offset_x: int = random.randint(-2, 2)
            offset_y: int = random.randint(-2, 2)
            yes_btn.rect.move_ip(offset_x, offset_y)
            
        yes_btn.draw(screen)
        no_btn.draw(screen)

    if not confirming_quit:
        # --- Draw Credits Link ---
        if credits_rect.collidepoint(mouse_pos):
            screen.blit(credits_surf_underlined, credits_rect)
        else:
            screen.blit(credits_surf_normal, credits_rect)

    pygame.display.flip()
    
    clock.tick(60) # Cap FPS

pygame.quit()
sys.exit()