---
title: Security, signing & size
description: Add or remove PDF passwords and restrictions, sign PDFs by hand or with a certificate, make them smaller, and repair damaged files.
---

# Security, signing & size

These tools protect a PDF with a password or restrictions (or remove them), sign it, make it smaller, and recover damaged files. In the app this category is the **Security** tab under **Documents**.

Sign PDF and Compress PDF work on the same open PDF as the other PDF tools. Protect PDF and Repair PDF keep their own file, because they also have to open files the other tools can't: password-protected PDFs and damaged ones. To open a PDF, drag it from the Explorer onto the tool, click **Open PDF…**, or click **Use** followed by the name of the PDF selected in the Explorer. Right-clicking a PDF in the Explorer also offers **Sign PDF** and **Protect PDF**. See [The Tessera window](/docs/interface) for the general controls.

Every tool saves a **new** file and leaves the original alone. When it's done, a **Saved** card lists the result with **Open**, **Show in folder** and **Keep editing this file**. Each run is listed in the [History](/docs/history), but passwords never are: the History records which files a tool used and made, never the options you typed.

## Protect PDF

Protect PDF encrypts a PDF with a password, restricts what readers may do with it, or both. When you open a PDF that is already protected, the tool offers to unlock it instead.

### How to use it

1. Open **Protect PDF** and open a PDF. Tessera reads its security first.
2. To require a password to open the file, type it in **Open password** and again in **Confirm**.
3. To limit what people can do, untick the actions under **Restrictions**.
4. Optionally type a **Permissions password** and choose the **Encryption**.
5. Click **Protect and save…**, choose a name and folder, and click **Save**.

You need an open password, at least one unticked restriction, or both. Otherwise the button stays greyed out and the bar says "Set an open password or untick a permission."

### Options

| Option | What it does | Default |
|---|---|---|
| **Open password** | The password needed to open the file. Leave it empty to let anyone open it. | Empty |
| **Confirm** | Type the open password again. A message tells you if they don't match. | |
| **Show passwords** | Shows the passwords as you type instead of dots. | Off |
| **Restrictions** | What readers may do: **Printing**, **High-quality printing**, **Copying text and images**, **Editing the content**, **Comments and annotations**, **Filling in forms**, **Inserting, deleting and rotating pages**, **Text access for screen readers**. Untick what you want to forbid. | All allowed |
| **Permissions password** | The password needed to change the restrictions. It must differ from the open password. If you leave it empty, Tessera makes up a random one and doesn't show it. | Empty (random) |
| **Encryption** | **AES 256-bit (recommended)**, AES 128-bit for older readers, or **RC4 128-bit (old readers)**. | AES 256-bit |

### Unlock

If the PDF you open is already protected, the tool says so. It tells you whether the file needs a password to open or only has restrictions, and lists what isn't allowed.

1. Type the password under **Remove the protection**. For a file that needs a password to open, this is the open or the permissions password.
2. Click **Unlock and save…**, choose a name and folder, and click **Save**.

The saved copy has no password and no restrictions. Only remove protection from documents you own or are allowed to change.

### Good to know

- The file is suggested as `name_protected.pdf` (or `name_unlocked.pdf`) next to the original.
- An open password is real encryption: without it, nobody can read the file. Restrictions are different. PDF readers are expected to respect them, but they aren't a strong barrier on their own.
- A file that opens without a password but has restrictions can be unlocked here without typing anything.
- Tessera can't protect a file that is already protected. Unlock it first.
- A password-protected PDF opens only in Protect PDF and [Repair PDF](#repair-pdf). Unlock a copy first to use it in the other tools.
- **Keep editing this file** opens the result in Protect PDF again, where it shows as protected.
- Passwords aren't stored anywhere, including the [History](/docs/history).

## Sign PDF

Sign PDF adds a signature in one of two ways. An **electronic signature** is a picture of your handwritten signature placed on the page. A **digital signature** uses a certificate, so anyone can check later whether the file was changed after signing.

### How to use it

1. Open **Sign PDF** and open a PDF.
2. Choose **Electronic signature** or **Digital signature (certificate)** at the top.
3. Follow the steps for that kind of signature below.

If the PDF already has digital signatures, a **Digital signatures in this file** card appears at the top. See [Checking signatures](#checking-signatures).

### Electronic signature

1. Make your signature in one of three ways:
   - **Draw**: sign in the box with your mouse, pen or finger. With a pen, pressing harder draws a thicker line.
   - **Type**: type your name and choose a handwriting style.
   - **Upload image**: click **Choose a signature image…** and pick a picture of your signature. A PNG with a transparent background looks best.
2. For **Draw** and **Type**, pick an ink colour and click **Use this signature**. **Clear** starts again.
3. Click on the page to place the signature, or drag to give it a size. Place it as many times as you need, on any page. Drag a signature to move it, drag its handles to resize it.
4. Optionally click **Add date** to add today's date as text. Select it to change the text in the box that appears.
5. Click **Save signed PDF…**, choose a name and folder, and click **Save**.

To remove a placed item, select it and press <kbd>Delete</kbd>, or click **Remove selected**. **New signature** lets you make a different one. The panel shows how many items you've placed and on which pages.

### Digital signature

1. Under **Certificate**, click **Choose .pfx / .p12…** and pick your certificate file. If you don't have one, click **Create a certificate…** (see below).
2. Type the **Certificate password** and click **Check** (or press <kbd>Enter</kbd>). Tessera shows who the certificate belongs to, who issued it (or "Self-signed") and until when it's valid.
3. Fill in the **Details**: **Reason**, **Location** and **Contact**.
4. Leave **Show a signature box on the page** ticked to add a visible box. Until you place it, it sits at the bottom right of the page you're looking at (the last page at first). Click on a page to put it there, and drag its edges to resize it.
5. Click **Sign and save…**, choose a name and folder, and click **Save**.

**Sign and save…** stays greyed out until the certificate has been checked, and for an expired certificate.

#### Create a certificate

1. Click **Create a certificate…**.
2. Fill in **Your name**, and optionally **Email**, **Organisation** and **Country (2 letters)**.
3. Choose a **Password (6+ characters)** and type it again in **Confirm**.
4. Click **Create and save…**. The Save dialog suggests `Your name certificate.pfx` in your Documents folder.

The new certificate is selected and checked straight away. Keep the file and its password safe: anyone who has both can sign as you.

### Options

Electronic signature:

| Option | What it does | Default |
|---|---|---|
| **Draw** / **Type** / **Upload image** | How you make the signature. | Draw |
| Style (Type) | **Segoe Script**, **Lucida Handwriting**, **Ink Free**, **Segoe Print** or **Brush Script MT**. | Segoe Script |
| **Ink** | Black, dark blue or dark green. | Black |
| **Add date** | Adds today's date as text near the bottom right of the page, in 11 pt Arial. | |

Digital signature:

| Option | What it does | Default |
|---|---|---|
| **Reason** | Why you sign. Stored in the signature and shown in the box. | `I approve this document` |
| **Location** | Where you sign. Stored in the signature. | Empty |
| **Contact** | How to reach you. Stored in the signature. | Empty |
| **Show a signature box on the page** | Adds a visible box reading "Digitally signed by" your name, the date and time, and the reason. | On |

### Checking signatures

When you open a signed PDF, each digital signature is listed with the signer's name, when it was signed, the reason, and one of these results:

| Message | Meaning |
|---|---|
| Intact: the document has not changed since it was signed. | The signature covers the whole file and still matches. |
| Intact, but content was added after signing (for example another signature). | The signed part is unchanged, and more was added afterwards. |
| The document was changed after it was signed — this signature no longer matches. | The signed content has been altered. |
| The signature is not valid. | The signature itself doesn't check out. |

When a signature is intact but its certificate is self-signed, or doesn't come from an authority Windows trusts, the message adds a note saying so.

### Good to know

- The file is suggested as `name_signed.pdf` next to the original.
- An electronic signature is a picture drawn into the page. It looks like a signature but doesn't protect the file from changes. In the History it's listed as "Edit PDF".
- A digital signature uses the PAdES format with SHA-256. Tessera adds it as an update at the end of the file, so the original content stays byte for byte as it was. Signing again adds another signature (named `Signature1`, `Signature2`…), and earlier signatures stay intact.
- The signing time comes from your computer's clock. No time-stamp server is contacted.
- A certificate you create is self-signed: an RSA 3072-bit key, valid for three years. It proves the file hasn't changed since you signed it, but PDF readers will show you as not verified. For a trusted signature, use a certificate from a certificate authority.
- Tessera remembers which certificate file you used last, but never its password.
- Checking signatures happens on your computer. Tessera doesn't download revocation lists or contact any server.
- Typed signatures use handwriting fonts that come with Windows. If one is missing, a generic handwriting-style font is used instead.
- A digital signature can't be added to a protected PDF, even one that only has restrictions. Remove the protection first with [Protect PDF](#protect-pdf).

## Compress PDF

Compress PDF makes a PDF smaller. It shrinks and re-encodes large pictures, merges duplicate parts of the file and compresses the page content.

### How to use it

1. Open **Compress PDF** and open a PDF.
2. Choose a level: **Light**, **Balanced** or **Strong**.
3. Optionally tick **Also remove metadata, thumbnails and embedded XMP**.
4. Click **Compress and save…**, choose a name and folder, and click **Save**.

When it's done, a card shows the size **Before** and **After**, how much was **Saved**, and how many pictures were re-encoded.

### Options

| Option | What it does | Default |
|---|---|---|
| **Light** | Pictures larger than 2400 pixels on their longest side are scaled down, and pictures are re-encoded as JPEG at quality 85. Best for printing. | |
| **Balanced** | Pictures up to 1600 pixels, JPEG quality 72. Good on screen and for email. | Selected |
| **Strong** | Pictures up to 1100 pixels, JPEG quality 55. Smallest file. | |
| **Also remove metadata, thumbnails and embedded XMP** | Also removes the document's properties (title, author, and so on) and its XMP metadata. | Off |

### Good to know

- The file is suggested as `name_compressed.pdf` next to the original.
- A picture is only replaced if the new version is at least 10% smaller.
- Some pictures are left as they are: ones with transparency or a mask, black-and-white scans (1-bit), and pictures stored as JBIG2, CCITT fax or JPEG 2000.
- Pictures that are re-encoded become JPEGs. CMYK pictures are converted to RGB, so for professional printing **Light** or no compression may be the better choice.
- Page thumbnails and leftover editing data are removed at every level, whether or not the box is ticked.
- If the file can't get smaller, the copy is saved unchanged and the card says "This PDF is already well optimised; the copy is unchanged."
- A password-protected PDF can't be compressed. Unlock a copy with [Protect PDF](#protect-pdf) first.

## Repair PDF

Repair PDF checks a PDF for damage, lists what's wrong, and rebuilds it so it opens again. It also works on files the other tools can't open.

### How to use it

1. Open **Repair PDF** and open a PDF. Tessera checks the file straight away.
2. Read the result: **No problems found**, or how many problems were found with a list of them (up to 12 are shown). It also shows the file size and how many pages can be read.
3. Click **Repair and save…**, choose a name and folder, and click **Save**.

Under the result, a line tells you which method recovered the file.

### Options

Repair PDF has no options. It tries every method and keeps the best result.

### Good to know

- The file is suggested as `name_repaired.pdf` next to the original.
- The check looks for a missing PDF header or end-of-file marker (a file that was cut short), tries to read the file strictly and leniently, tries to open it with the PDF renderer, and collects any warnings.
- The repair tries these methods and keeps the one that recovers the most pages:
  - rewriting the file with a fresh cross-reference table, skipping pages that are broken,
  - the PDF renderer's own recovery mode,
  - for a file that was cut short, scanning it for every complete object and adding a new index, either using the document's own page list or building a new one from every page found.
- A page list built from scratch puts pages in the order they appear in the file, which may not be the original order.
- If no method recovers a single page, you get the message "The file is too damaged to recover any pages".
- You can repair a healthy file too, for example to drop leftover data.
- **Keep editing this file** opens the repaired PDF in [Edit PDF](/docs/edit).
