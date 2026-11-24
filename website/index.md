---
layout: home
title: Tilepress
titleTemplate: Free PDF and image tools that run on your PC
description: Tilepress is a free, open-source Windows app with 39 PDF and image tools. Merge, convert, compress, sign and OCR PDFs; resize, convert, retouch and upscale photos. Nothing is uploaded.

hero:
  name: Tilepress
  text: PDF and image tools that run on your own computer
  tagline: Merge, convert, compress, sign and OCR PDFs. Resize, convert, retouch and upscale photos. 39 tools, free and open source, and your files never leave your PC.
  image:
    src: /favicon.svg
    alt: ''
  actions:
    - theme: brand
      text: Download for Windows
      link: /download
    - theme: alt
      text: See all 39 tools
      link: '#tools'
    - theme: alt
      text: Source on GitHub
      link: https://github.com/epicabdou/tilepress

features:
  - icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="11" rx="2.5"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
    title: Nothing leaves your PC
    details: Files are opened, changed and saved on your computer. No uploads, no account, no telemetry.
  - icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></svg>
    title: 39 tools, one window
    details: The PDF and image tools you already know by name, side by side with your folders and a live preview.
  - icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/></svg>
    title: Free and open source
    details: GNU GPL v3. No ads, no premium tier, no watermarks on your files. Read the code, change it, share it.
  - icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M4 12h16M4 17h10"/><path d="m17 15 2 2 3-4"/></svg>
    title: No size or batch limits
    details: Big PDFs, whole folders of photos. The only limit is your computer.
  - icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8.5a15 15 0 0 1 20 0M5.5 12a10 10 0 0 1 13 0M9 15.5a5 5 0 0 1 6 0"/><path d="M12 19h.01"/><path d="M3 3l18 18"/></svg>
    title: Works offline
    details: Everything runs locally. Only the LaTeX engine and the AI models are downloaded, once, the first time you need them.
  - icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 12a8.5 8.5 0 1 0 2.5-6"/><path d="M3.5 4v4h4"/><path d="M12 7.5V12l3 2"/></svg>
    title: Remembers what you made
    details: A searchable history of every file each tool produced, and the files it came from. Yours alone, and you can turn it off.
---

<div class="home-body">

<section class="home-section">
  <h2>See it in action</h2>
  <p class="lede">Real screenshots of the app, not mock-ups.</p>
  <Showcase />
</section>

<section class="home-section" id="tools">
  <h2>Every tool you need</h2>
  <p class="lede">Each one has a full guide in the docs. Click a tool to read it.</p>
  <ToolGrid />
</section>

<section class="home-section narrow">
  <h2>Coming from iLovePDF or iLoveIMG?</h2>
  <p class="lede">You'll find the tools you use there under the same names: Merge PDF, Compress PDF, PDF to Word, Convert to JPG, Remove background and the rest. The difference is where the work happens.</p>
  <Comparison />
  <p class="fine">A few online-only extras, such as comparing or translating PDFs, aren't in Tilepress yet. iLovePDF and iLoveIMG are trademarks of their owners; Tilepress is an independent project and is not affiliated with them.</p>
</section>

<section class="home-section cta">
  <h2>Get Tilepress</h2>
  <p class="lede">One installer, no admin rights needed. Free forever.</p>
  <DownloadPanel />
</section>

</div>
