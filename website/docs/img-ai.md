---
title: AI enhancements
description: Upscale pictures with AI, remove or replace backgrounds, and find and blur faces, all on your own PC.
---

# AI enhancements

These tools are under the **AI** tab in the **Images** section. Upscale Image and Remove background run AI models on your computer, and Blur face uses the face detector built into Windows. Your pictures are never uploaded.

All three work on one image at a time. They share the open image with Crop Image and the Photo editor, so a picture you open in one is open in the others. To open an image, drag it from the Explorer onto the tool, click **Open image…**, or select it in the Explorer and click the **Use** button with its name. Right-clicking an image in the Explorer also offers **Upscale image** and **Remove background**. See [The Tilepress window](/docs/interface) for the Explorer and the other general controls.

Each tool saves a new file and never changes the original. After saving, the **Saved** card offers **Open**, **Show in folder** and **Keep editing this file**, which opens the saved copy in the tool.

::: tip Models are downloaded on first use
Upscale Image and Remove background each need a model file. Nothing is downloaded until you first use the tool, and the tool tells you beforehand what it will download. After that, it works offline. See [Privacy](/docs/privacy) for exactly what is downloaded and from where.
:::

## Upscale Image

Upscale Image makes a picture two or four times larger with Real-ESRGAN, an AI super-resolution model. It rebuilds sharp detail instead of just stretching the pixels, which helps when a small or low-resolution picture has to be shown or printed bigger.

### How to use it

1. Open an image.
2. Under **Scale**, choose **2×** or **4×**. Each card shows the size in pixels the result will have.
3. If you like, tick **Extra sharpening**, and choose the **Format** (and the **Quality** for JPG, WebP or AVIF).
4. Click **Upscale 4× and save…** (or **Upscale 2× and save…**) and choose where to save the file.
5. Wait while it works. The progress bar shows the model download the first time, then the tiles as they are processed.
6. When it's done, a before/after slider replaces the picture. Drag the divider to compare. Click **2× zoom**, **3× zoom** or **4× zoom** to magnify both sides, and move the pointer over the picture to look around. **Fit** shows the whole picture again.

Under the button, a line tells you where the model ran: "Ran on the GPU (DirectML)." or "Ran on the CPU."

### Options

| Option | What it does | Default |
|---|---|---|
| **Scale** | **2×** or **4×** the width and height. | 4× |
| **Extra sharpening** | Sharpens the result a little more after upscaling. | Off |
| **Format** | PNG, JPG, WebP or AVIF. | PNG |
| **Quality** | 10 to 100. Shown for JPG, WebP and AVIF only. | 92 |

### Good to know

- **Inputs:** JPG, PNG, WebP, HEIC/HEIF, AVIF, GIF, BMP, TIFF and ICO.
- **Size limits:** 4× takes pictures up to 4.2 megapixels, and 2× up to 16 megapixels, so the result stays around 64 megapixels at most. For a bigger picture, the tool says so and the button is disabled. Choose 2×, or make the picture smaller first with [Crop Image](/docs/img-layout) or [Resize Image](/docs/img-optimize).
- **File name:** the suggested name is the original name plus `_x4` or `_x2`, next to the original, for example `holiday_x4.png`. If that file exists, a number is added, as in `holiday_x4 (2).png`.
- The model always works at 4×. The 2× result is the 4× result reduced by half, which keeps the rebuilt detail.
- The picture is processed in small overlapping tiles, so there are no seams between them.
- Transparency is kept, but it's enlarged the ordinary way, not by the model. If you save a transparent picture as JPG, the transparent areas become white.
- The saved file keeps the picture's metadata and colour profile. Its DPI is multiplied by the scale, so the printed size stays the same.
- **Model:** the first upscale downloads Real-ESRGAN General x4v3, about 4.5 MB (BSD-3-Clause licence, from Qualcomm AI Hub). It's checked against a checksum and kept for next time.
- **Graphics card:** the model runs on your graphics card through DirectML when it can. If there's no suitable graphics card, it runs on the processor, which is slower.

## Remove background

Remove background finds the subject of a picture with ISNet, an AI segmentation model, and removes everything else. You can leave the background transparent, fill it with a colour, or replace it with a blurred copy of the picture.

### How to use it

1. Open an image.
2. Click **Remove the background** under the picture. The first time, this downloads the model. Then the tool finds the subject ("Finding the subject…").
3. Under **Background**, choose **Transparent**, **Colour** or **Blurred**.
4. Adjust the **Edges** if you need to. The preview updates as you change the options, without running the model again. A checkerboard shows the transparent areas.
5. To check the result, tick **Compare with the original** and drag the divider.
6. Choose the **Format** and click **Save…**.

### Options

| Option | What it does | Default |
|---|---|---|
| **Background** | **Transparent**, **Colour** (a solid colour) or **Blurred** (a blurred copy of the picture). | Transparent |
| Colour swatches | With **Colour**: white, black, light grey, blue, green, red or yellow, or any colour from the colour picker. | White |
| **Blur** | With **Blurred**: 5 to 100. How blurred the background is. | 50 |
| **Clean-up** | 0 to 90. Firms up soft, hazy edges. Higher values give a cleaner cut-out. | 40 |
| **Soften** | 0 to 12 px, in half-pixel steps. Feathers the edge of the subject. | 0 px |
| **Trim to the subject** | With **Transparent**: crops the result to the subject, with a small margin. | Off |
| **Compare with the original** | Shows a before/after slider. It appears once the preview is ready. | Off |
| **Format** | PNG, WebP or AVIF for a transparent background. JPG is also offered for **Colour** and **Blurred**. | PNG |

### Good to know

- **Inputs:** JPG, PNG, WebP, HEIC/HEIF, AVIF, GIF, BMP, TIFF and ICO.
- **File name:** the suggested name is the original name plus `_no_bg`, next to the original, for example `portrait_no_bg.png`.
- The model runs once per picture. Changing the options afterwards reuses its result, so it's instant. While the app is open, Tilepress remembers the result for the last few pictures. If the file changes, the model runs again.
- The model looks at the whole picture at once (at 1024 × 1024 pixels). The saved file is full size.
- Areas that were already transparent in the original stay transparent.
- The quality for JPG, WebP and AVIF is fixed at 92.
- The saved file keeps the picture's metadata and colour profile.
- **Model:** the first use downloads ISNet (general use), about 179 MB (Apache-2.0 licence, from the rembg project's release on GitHub). It's checked against a checksum and kept for next time.
- **Graphics card:** like Upscale Image, it runs on your graphics card through DirectML when it can, otherwise on the processor.

## Blur face

Blur face finds the faces in a photo and blurs, pixelates or covers them, for example before you share a picture of people who shouldn't be recognisable. You can check every box before saving, and add your own for anything else you want hidden.

### How to use it

1. Open a photo. Tilepress looks for faces straight away ("Looking for faces…") and puts a box on each face it finds. The picture shows the real result.
2. Check the boxes. Click a box to select it, then drag it to move it, or drag its handles to resize it. To remove the selected box, click **Remove selected** or press <kbd>Delete</kbd>.
3. To hide something it missed, click **+ Add a box**, then drag over the area on the photo. A single click adds a square box centred where you click.
4. Under **Effect**, choose **Blur**, **Pixelate** or **Cover**, and adjust the options.
5. Choose the **Format** and click **Blur and save…**.

Untick **Show boxes** to see the result without the box outlines. **Detect again** discards your boxes and looks for faces again.

### Options

| Option | What it does | Default |
|---|---|---|
| **Effect** | **Blur**, **Pixelate**, or **Cover** with a solid colour. | Blur |
| **Strength** | With **Blur** and **Pixelate**: 10 to 100. | 60 |
| **Colour** | With **Cover**: the colour of the cover. | Black |
| **Grow boxes** | 0 to 60%. Enlarges each box, because a face is usually a little bigger than the box the detector finds. | 15% |
| **Oval** / **Rectangle** | The shape of the hidden area. | Oval |
| **Format** | Same as the original, JPG, PNG or WebP. | Same as the original |
| **Show boxes** | Shows or hides the box outlines on screen. It doesn't change the saved file. | On |

### Good to know

- **Inputs:** JPG, PNG, WebP, HEIC/HEIF, AVIF, GIF, BMP, TIFF and ICO. With **Same as the original**, HEIC photos are saved as JPG and ICO files as PNG.
- **File name:** the suggested name is the original name plus `_blurred`, next to the original, for example `team_blurred.jpg`.
- Faces are found with the face detector built into Windows, so there's nothing to download. Large photos are checked at 2048 pixels and then also in full-resolution tiles, so small faces in group photos are found too.
- The detector can miss faces, so look over the whole photo before you save. **Blur and save…** stays disabled until there is at least one box.
- Blur and pixelate fade out softly at the edge of each box. Cover has a hard edge.
- The saved copy leaves out the photo's metadata, such as the camera and the location, and its colour profile. There's no option to keep them.
- The quality for JPG and WebP is fixed at 92.
