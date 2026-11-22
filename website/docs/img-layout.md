---
title: Crop, rotate & capture
description: Crop an image to a box, circle or aspect ratio, rotate or flip many images at once, and turn a web page or HTML into a picture.
---

# Crop, rotate & capture

These tools change the frame of a picture, or make a new one from a web page. They read JPG, PNG, WebP, HEIC/HEIF (iPhone), AVIF, GIF, BMP, TIFF and ICO, and save JPG, PNG, WebP or AVIF, or keep the original's format (HTML to Image saves PNG, JPG or WebP). Every tool saves a new file and never changes the original. See [The Tessera window](/docs/interface) for the Explorer, the Preview pane and the Saved card.

- **Crop Image** works on one image. It shares the open image with Upscale Image, Remove background, Blur face and the Photo editor, so you can switch between them without opening it again.
- **Rotate Image** works on a list. Add images with **Add images…** or by dragging them from the Explorer, and remove them with the × on each row or **Clear list**. It saves next to each image, or in a folder you choose.
- **HTML to Image** makes a new picture from a web address, an HTML file or HTML code.

## Crop Image

Trims the edges of an image, or frames it to an exact aspect ratio. You can also crop to a circle or oval, with a transparent outside.

### How to use it

1. In the **Images** section, open the **Frame** tab and choose **Crop Image**.
2. Open an image: click **Open image…**, drag one from the Explorer, or click **Use** followed by the name of the image selected in the Explorer. You can also right-click an image in the Explorer and choose **Crop image**.
3. Set the crop box on the picture:
   - Drag inside the box to move it.
   - Drag a corner or an edge to resize it.
   - Drag outside the box to draw a new one.

   The box shows its size in pixels and rule-of-thirds guides.
4. If you want a fixed shape, pick an **Aspect ratio**, or type exact values under **Area (pixels)**.
5. Choose the **Shape**, **Format** and **Quality**.
6. Click **Crop and save…** and choose a name and folder in the Save dialog.

To work on another image, use **Change…** in the bar above the picture, or **Close** it.

### Options

| Option | What it does | Default |
|---|---|---|
| **Aspect ratio** | **Free**, **Original** (the image's own proportions), **1:1**, **4:3**, **3:4**, **16:9**, **9:16**, **3:2**, **2:3**, **5:4** or **4:5**. Picking a ratio resets the box to the largest centred box with that ratio. | Free |
| **Area (pixels)** | **X**, **Y**, **Width** and **Height** of the box. With a fixed ratio, changing the width changes the height to match, and the other way round. The box always stays inside the image. | The middle 80% of the image |
| **Shape** | **Rectangle**, or **Circle / oval**: only the oval inside the box is kept, and the outside becomes transparent. Use **1:1** for a perfect circle. | Rectangle |
| **Format** | **Same as the original**, **JPG**, **PNG**, **WebP** or **AVIF**. | Same as the original |
| **Quality** | 10 to 100. Hidden when the file is saved as PNG. | 92 |

### Good to know

- The Save dialog suggests the original's name with `_cropped` added, in the same folder, for example `portrait_cropped.jpg`.
- With a fixed aspect ratio, the box has corner handles only, so it keeps its shape.
- JPG can't store transparency, so a **Circle / oval** crop is saved as PNG unless you choose WebP or AVIF (or the original already is PNG, WebP or AVIF and you keep its format). This happens even if you choose JPG.
- Pixel positions refer to the image as you see it, upright.
- **Same as the original** saves HEIC/HEIF photos as JPG and ICO files as PNG.
- The camera details and the colour profile are kept.
- In the **Saved** card, **Keep editing this file** opens the cropped copy, so you can carry on with it in this tool or another image tool.

## Rotate Image

Turns images by 90°, 180° or 270°, or mirrors them. Set each image on its own, or change all of them at once.

### How to use it

1. In the **Images** section, open the **Frame** tab and choose **Rotate Image**.
2. Click **Add images…**, or drag images from the Explorer onto the list.
3. Turn or flip each image with the buttons on its row: **Rotate left**, **Rotate right**, **Flip horizontally** (⇋) and **Flip vertically** (⇵). The thumbnail shows the result.
4. Or use the buttons after **All images:** to change every image in the list: **Left**, **Right**, **180°**, **Flip horizontally** and **Flip vertically**. **Reset** undoes all turns and flips.
5. Choose the **Format** and **Quality**, and where to save.
6. Click **Rotate and save** (or **Rotate and save 3 images**).

### Options

| Option | What it does | Default |
|---|---|---|
| **Format** | **Same as the original**, **JPG**, **PNG**, **WebP** or **AVIF**. | Same as the original |
| **Quality** | 10 to 100. Used for JPG, WebP and AVIF. | 95 |
| Where to save | **Save next to each image**, or **Save in a folder**. | Save next to each image |

### Good to know

- Only the images you turned or flipped are saved. If you haven't changed any, the action bar says "Turn or flip at least one image."
- New files are named after the original with `_rotated` added, for example `scan_rotated.jpg`.
- The picture is turned and then saved again, so JPG, WebP and AVIF files are re-encoded at the **Quality** you set.
- Photos are shown upright first (the camera's rotation flag is applied), so turns are relative to what you see. The saved file is upright and has no rotation flag.
- The camera details and the colour profile are kept.
- Animated GIFs and multi-page TIFFs are saved as a single picture: only the first frame or page is kept.

## HTML to Image

Renders a web page, an HTML file or a snippet of HTML and CSS into a PNG, JPG or WebP picture. You can capture the whole page or just the visible area, at the width of any screen.

### How to use it

1. In the **Images** section, open the **Frame** tab and choose **HTML to Image**.
2. Choose the source:
   - **Web page**: type the address in the box, for example `example.com`.
   - **HTML file**: click **Choose an HTML file…** and pick an `.html`, `.htm`, `.xhtml` or `.svg` file.
   - **HTML code**: type or paste HTML in the box. It starts with a small sample you can replace.
3. Set the options (see below). The action bar shows the width of the picture, for example "1280px wide at 2× → 2560px".
4. Click **Capture and save…** and choose a name and folder in the Save dialog. The button says **Rendering…** while it works.
5. When it's done, the **Saved** card appears, with the captured picture below it.

### Options

| Option | What it does | Default |
|---|---|---|
| **Screen width** | **Desktop (1440 px)**, **Laptop (1280 px)**, **Tablet (768 px)**, **Phone (390 px)** or **Custom…**. The page is laid out as on a screen this wide. | Laptop (1280 px) |
| **Width (px)** | With **Custom…**: any width from 320 to 3840 px. | 1000 |
| **Capture** | **The whole page**, from top to bottom, or **The visible area only**. | The whole page |
| **Visible height (px)** | With **The visible area only**: the height of the screen, from 200 to 4000 px. | 800 |
| **Sharpness** | **1× (standard)**, **2× (retina)** or **3×**. Multiplies the number of pixels, for sharp text on high-resolution screens. | 1× (standard) |
| **Format** | **PNG**, **JPG** or **WebP**. | PNG |
| **Quality** | 10 to 100, for JPG and WebP. | 90 |
| **Wait after loading (s)** | Extra time to wait after the page has loaded, from 0 to 30 seconds. Useful for pages that animate or load content late. | 0 |
| **Transparent background (for snippets and pages without a background)** | For PNG and WebP. Areas without a background colour stay transparent instead of white. | Off |

### Good to know

- Only `http://` and `https://` addresses work. If you leave out the start, Tessera adds `https://`.
- The page is rendered by WebView2, the engine that also draws Tessera, in a window kept off-screen, out of sight and out of the taskbar. The page runs as it would in a browser, scripts included. Only one page is rendered at a time.
- Tessera waits up to 60 seconds for the page to load, then up to 15 seconds more for its fonts and images. For **The whole page**, it also scrolls through the page first so lazy-loaded pictures appear, then goes back to the top.
- Widths under 600 px are rendered as on a phone.
- Scroll bars are hidden in the picture.
- **The whole page** is captured up to 16,000 pixels tall (before **Sharpness** is applied). A longer page is cut off at that point.
- Suggested names: for a web page, a name taken from the address in your Downloads folder, such as `example.com.png`; for an HTML file, the file's name with the picture's extension, in the same folder; for HTML code, `snippet.png` in your Downloads folder.
- Pasted code that isn't a complete page is wrapped in one. Because it's rendered from a temporary folder, relative links to pictures or stylesheets won't find your files. Save the HTML as a file next to them and use **HTML file** instead.
- Saved pictures contain no metadata.
- If the page can't be reached, you'll see "The page couldn't be loaded. Check the address and your internet connection."

::: warning Uses the internet
A **Web page** is downloaded from the internet, with everything it links to. An **HTML file** or **HTML code** can also fetch pictures, fonts or scripts from the internet if it links to them. See [Privacy](/docs/privacy).
:::

To turn HTML into a PDF instead, use **HTML to PDF** in [Convert to PDF](/docs/to-pdf).
