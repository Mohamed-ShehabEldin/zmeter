import os
import sys
import tempfile
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPixmap
import gc

# Platform detection
_is_windows = sys.platform.startswith('win')
_win32com_available = False

if _is_windows:
    try:
        import win32com.client
        _win32com_available = True
    except ImportError:
        print("Warning: win32com not available. PowerPoint live updating will not be available.")
else:
    # Use python-pptx on macOS/Linux
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.enum.shapes import MSO_SHAPE
    except ImportError:
        print("Warning: python-pptx not available. PowerPoint functionality unavailable.")

def add_slide_with_qpixmap(ppt_path, slide_title, slide_text, pixmap_images, image_positions):
    """
    Add a slide with QPixmap images to a PowerPoint presentation.
    
    On Windows: Uses win32com for live updating while PowerPoint is open
    On macOS/Linux: Uses python-pptx to create/modify the file (no live updating)
    
    Args:
        ppt_path: Path to the PowerPoint file
        slide_title: Title text for the slide
        slide_text: Body text for the slide
        pixmap_images: List of QPixmap objects (must be exactly 3)
        image_positions: List of tuples (left, top, width, height) for image placement
    """
    if len(pixmap_images) != 3:
        raise ValueError("Exactly three QPixmap objects must be provided.")

    # Convert QPixmap objects to temporary image files
    temp_files = []
    for i, pixmap in enumerate(pixmap_images):
        temp_path = os.path.join(tempfile.gettempdir(), f"temp_image_{i}.png")
        pixmap.save(temp_path, "PNG")
        temp_files.append(temp_path)

    if _is_windows and _win32com_available:
        _add_slide_win32com(ppt_path, slide_title, slide_text, temp_files, image_positions)
    else:
        _add_slide_python_pptx(ppt_path, slide_title, slide_text, temp_files, image_positions)


def _add_slide_win32com(ppt_path, slide_title, slide_text, temp_files, image_positions):
    """Windows implementation using win32com (live updating)."""
    # Connect to PowerPoint application
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    ppt_app.Visible = True

    # Open or create the presentation
    if not os.path.exists(ppt_path):
        presentation = ppt_app.Presentations.Add()
        presentation.SaveAs(ppt_path)
    else:
        presentation = None
        for pres in ppt_app.Presentations:
            if os.path.normcase(pres.FullName) == os.path.normcase(ppt_path):
                presentation = pres
                break
        if presentation is None:
            presentation = ppt_app.Presentations.Open(ppt_path, ReadOnly=False, Untitled=False, WithWindow=True)

    # Add a new blank slide (layout index may vary; here 12 is assumed to be blank)
    num_slides = presentation.Slides.Count
    blank_layout = 12
    slide = presentation.Slides.Add(num_slides + 1, blank_layout)

    # Add title and text boxes
    title_box = slide.Shapes.AddTextbox(Orientation=1, Left=50, Top=15, Width=600, Height=50)
    title_box.TextFrame.TextRange.Text = slide_title
    text_box = slide.Shapes.AddTextbox(Orientation=1, Left=50, Top=40, Width=600, Height=100)
    text_box.TextFrame.TextRange.Text = slide_text
    
    for temp_path, pos in zip(temp_files, image_positions):
        left, top, width, height = pos
        slide.Shapes.AddPicture(FileName=temp_path,
                                  LinkToFile=False,
                                  SaveWithDocument=True,
                                  Left=left,
                                  Top=top,
                                  Width=width,
                                  Height=height)

    presentation.Save()

    # Clean up COM objects
    del presentation, ppt_app
    gc.collect()


def _add_slide_python_pptx(ppt_path, slide_title, slide_text, temp_files, image_positions):
    """macOS/Linux implementation using python-pptx (file-based, no live updating)."""
    print(f"[macOS/Linux Mode] Adding slide to PowerPoint file (no live updating)")
    
    # Open existing presentation or create new one
    if os.path.exists(ppt_path):
        presentation = Presentation(ppt_path)
    else:
        presentation = Presentation()
    
    # Add a blank slide
    blank_slide_layout = presentation.slide_layouts[6]  # Layout 6 is typically blank
    slide = presentation.slides.add_slide(blank_slide_layout)
    
    # Add title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(6.0), Inches(0.5))
    title_frame = title_box.text_frame
    title_frame.text = slide_title
    title_frame.paragraphs[0].font.size = Pt(28)
    
    # Add text
    text_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.75), Inches(6.0), Inches(1.0))
    text_frame = text_box.text_frame
    text_frame.word_wrap = True
    text_frame.text = slide_text
    
    # Add images
    for temp_path, pos in zip(temp_files, image_positions):
        left, top, width, height = pos
        # Convert from EMUs (English Metric Units) to inches if needed
        # python-pptx uses inches by default
        slide.shapes.add_picture(temp_path, Inches(left/914400), Inches(top/914400), 
                                width=Inches(width/914400), height=Inches(height/914400))
    
    # Save the presentation
    presentation.save(ppt_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = QWidget()
    widget.resize(300, 200)
    widget.show()
    app.processEvents()

    # Grab images from the widget
    image1 = widget.grab()
    image2 = widget.grab()
    image3 = widget.grab()

    ppt_file = r"C:\Users\moham\OneDrive\Documents\test_presentation.pptx"
    title = "Slide with QPixmap Images"
    text = "This slide contains three images grabbed from PyQt widgets."

    add_slide_with_qpixmap(ppt_file, title, text, [image1, image2, image3])
    
    # Do not call app.exec_() to avoid blocking; close the application instead.
    widget.close()
    app.exit()
