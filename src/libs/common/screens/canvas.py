import pygame
import pickle
import os
import sys
from typing import Optional, Union, Any, List, Tuple, Dict, Callable, Type
from libs.utils.pylog import Logger

# Add libs to path if not already present (for utility imports)
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

logger = Logger(__name__)

# --- tkinter Setup ---
# Attempts to import tkinter for file dialogs.
try:
    import tkinter as tk
    from tkinter import filedialog
    
    def get_tk_root() -> tk.Tk:
        """
        Creates a hidden tkinter root window, sets it to be 'topmost' 
        to appear over other windows (like pygame), and returns it.
        """
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        try:
            # Attempt to make the dialog window appear on top
            root.call('wm', 'attributes', '.', '-topmost', True)
        except Exception as e:
            logger.warning(f"Warning: Could not set topmost attribute for tkinter: {e}")
        return root
except ImportError:
    logger.warning("Warning: tkinter module not found. File dialogs will not work.")
    tk = None  # Flag that tkinter is not available

class Surface:
    """
    Manages the state of the drawing surface, including its history (for undo/redo)
    and file operations (save, open, export).
    """
    
    def __init__(self, width: int, height: int, max_history_size: int = 30):
        """
        Initializes the DrawingCanvas.

        Args:
            width: The width of the drawing surface (WORLD_WIDTH).
            height: The height of the drawing surface (WORLD_HEIGHT).
            max_history_size: The maximum number of undo steps to store.
        """
        self.width: int = width
        self.height: int = height
        self.MAX_HISTORY_SIZE: int = max_history_size

        # Core canvas state
        self.drawing_surface: pygame.Surface = pygame.Surface((self.width, self.height))
        self.drawing_surface.fill("White")
        
        # Metadata
        self.is_dirty: bool = False
        self.current_project_path: Optional[str] = None
        
        # History state
        self.history: List[Tuple[pygame.Surface, str]] = []
        self.history_index: int = -1 # Point to -1 (no items)
        
        # Add the initial blank state
        self.add_history("Initial", self.drawing_surface)

    def set_history_state(self, index: int) -> Optional[pygame.Surface]:
        """
        Sets the canvas to a specific state from the history buffer.

        Args:
            index: The index in the `history` list to load.
            
        Returns:
            The new pygame.Surface if successful, else None.
        """
        if 0 <= index < len(self.history):
            self.history_index = index
            # Load a copy of the surface from history
            self.drawing_surface = self.history[self.history_index][0].copy()
            self.is_dirty = True # Changing history state counts as an unsaved change
            return self.drawing_surface
        return None
        
    def add_history(self, action_name: str, current_surface: pygame.Surface) -> Optional[int]:
        """
        Saves the current state of the canvas to the history list.

        Args:
            action_name: A descriptive name for the action (e.g., "Draw Line").
            current_surface: The *live* drawing surface from the main app.
            
        Returns:
            The recommended scroll offset for the history menu.
        """
        # If we undid and then drew, clear the "redo" future
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            
        # Limit history size
        if len(self.history) >= self.MAX_HISTORY_SIZE:
            self.history.pop(0)
            
        # Add a copy of the current surface
        self.history.append((current_surface.copy(), action_name))
        self.history_index = len(self.history) - 1
        self.is_dirty = True
        
        # Return the recommended scroll offset
        max_scroll: int = max(0, len(self.history) - 30)
        return max_scroll
        
    def undo(self) -> Optional[pygame.Surface]:
        """Moves the `history_index` back by one and loads that state."""
        if self.history_index > 0:
            return self.set_history_state(self.history_index - 1)
        return None

    def redo(self) -> Optional[pygame.Surface]:
        """Moves the `history_index` forward by one and loads that state."""
        if self.history_index < len(self.history) - 1:
            return self.set_history_state(self.history_index + 1)
        return None

    def clear_canvas(self) -> pygame.Surface:
        """
        Fills the `drawing_surface` with white, resets the history list, 
        and sets the project path to None.
        
        Returns:
            The new, cleared pygame.Surface.
        """
        self.drawing_surface.fill("White")
        self.history = []
        # We pass self.drawing_surface because it's the one we just cleared
        self.add_history("Initial", self.drawing_surface) 
        self.is_dirty = False
        self.current_project_path = None
        return self.drawing_surface

    def save_vecbo(self, current_surface: pygame.Surface) -> bool:
        """
        Saves the current canvas to the file specified by `current_project_path`.
        If no path is set, it calls `save_as_vecbo()`.

        Args:
            current_surface: The *live* drawing surface from the main app.

        Returns:
            True if saving was successful, False otherwise.
        """
        if not self.current_project_path:
            return self.save_as_vecbo(current_surface)
        
        if tk is None: 
            logger.warning("Cannot save: tkinter not available.")
            return False

        try:
            # Prepare data for pickling
            data: Dict[str, Any] = {
                "version": 1,
                "drawing_surface": pygame.image.tostring(current_surface, 'RGBA'),
                "size": (self.width, self.height)
            }
            with open(self.current_project_path, 'wb') as f:
                pickle.dump(data, f)
            self.is_dirty = False
            logger.info(f"Project saved to {self.current_project_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False

    def save_as_vecbo(self, current_surface: pygame.Surface) -> bool:
        """
        Uses a tkinter file dialog to ask the user for a save location.
        If a path is chosen, it sets `current_project_path` and calls `save_vecbo()`.

        Args:
            current_surface: The *live* drawing surface from the main app.

        Returns:
            True if saving was successful, False otherwise.
        """
        if tk is None: 
            logger.warning("Cannot save: tkinter not available.")
            return False

        root = get_tk_root()
        file_path: Optional[str] = filedialog.asksaveasfilename(
            defaultextension=".vecbo",
            filetypes=[("DrawingGuess Vector Board", "*.vecbo")],
            title="Save Project As"
        )
        root.destroy()
        
        if file_path:
            self.current_project_path = file_path
            return self.save_vecbo(current_surface)
        return False
        
    def open_file(self) -> Optional[pygame.Surface]:
        """
        Uses a tkinter file dialog to ask the user for a file to open.
        If a file is chosen, it loads the pickled data, updates the
        `drawing_surface`, and resets the history.

        Returns:
            The new pygame.Surface if loading was successful, else None.
        """
        if tk is None: 
            logger.warning("Cannot open: tkinter not available.")
            return None

        root = get_tk_root()
        file_path: Optional[str] = filedialog.askopenfilename(
            defaultextension=".vecbo",
            filetypes=[("DrawingGuess Vector Board", "*.vecbo")],
            title="Open Project"
        )
        root.destroy()
        
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    data: Dict[str, Any] = pickle.load(f)
                
                # Reconstruct the surface from pickled data
                surface_data: bytes = data["drawing_surface"]
                surf_size: Tuple[int, int] = data["size"]
                new_surf: pygame.Surface = pygame.image.fromstring(surface_data, surf_size, 'RGBA')

                # Update internal state
                self.drawing_surface = new_surf
                self.current_project_path = file_path
                self.is_dirty = False
                
                # Reset history with the loaded file
                self.history = []
                self.add_history(f"Opened: {os.path.basename(file_path)}", self.drawing_surface)
                
                logger.info(f"Project loaded from {file_path}")
                return self.drawing_surface
            except Exception as e:
                logger.error(f"Error opening file: {e}")
                return None
        return None

    def export_as_image(self, current_surface: pygame.Surface) -> bool:
        """
        Uses a tkinter file dialog to ask the user for a save location
        to export the canvas as a PNG or JPEG image.

        Args:
            current_surface: The *live* drawing surface from the main app.
            
        Returns:
            True if exporting was successful, False otherwise.
        """
        if tk is None: 
            logger.warning("Cannot export: tkinter not available.")
            return False

        root = get_tk_root()
        file_path: Optional[str] = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg;*.jpeg")],
            title="Export Canvas as Image"
        )
        root.destroy()
        
        if file_path:
            try:
                pygame.image.save(current_surface, file_path)
                logger.info(f"Canvas exported to {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error exporting image: {e}")
                return False
        return False