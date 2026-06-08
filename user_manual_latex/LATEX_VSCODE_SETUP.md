# Setting up LaTeX + VS Code from scratch (Windows)

A project-agnostic guide for getting LaTeX to compile inside VS Code, based on a
working `latexmk` setup. Nothing here depends on what the document is about — it's
purely the toolchain.

The end result: you press one button (or save the file) and VS Code builds your
PDF, handles the bibliography automatically, and shows the output next to your
source with click-to-jump between PDF and code.

---

## The three pieces

| Piece | Role | What we use |
|---|---|---|
| **A LaTeX distribution** | The actual compilers (`pdflatex`, `biber`, etc.) | MiKTeX |
| **A build orchestrator** | Runs the compilers in the right order, the right number of times | `latexmk` (ships with MiKTeX) |
| **The VS Code extension** | Hooks the build into the editor, previews the PDF | **LaTeX Workshop** |

You install the first one, the second comes for free, and the third is a VS Code
extension. Then a tiny config file (`latexmkrc`) ties it together.

---

## Step 1 — Install a LaTeX distribution (MiKTeX)

1. Download MiKTeX from <https://miktex.org/download> and run the installer.
2. During install, choose **"Install missing packages on the fly: Yes"**. This is
   the killer feature — MiKTeX downloads any package your document `\usepackage`s
   the first time it's needed, so you never hunt for packages manually.
3. After installing, open **MiKTeX Console** → **Updates** → check for and install
   updates once. (Do this occasionally.)

**Verify it worked.** Open a *new* terminal (PowerShell) and run:

```powershell
latexmk --version
pdflatex --version
biber --version
```

All three should print a version. If they're "not recognized", MiKTeX's `bin`
folder isn't on your `PATH` — reopen the terminal, or add it manually. On this
machine it lives at:

```
C:\Users\<you>\AppData\Local\Programs\MiKTeX\miktex\bin\x64
```

> **TeX Live instead?** Everything below works identically — TeX Live also ships
> `latexmk` and `biber`. The only difference is the installer. Pick one; don't
> install both.

---

## Step 2 — Install VS Code extensions

In VS Code, open the Extensions panel (`Ctrl+Shift+X`) and install:

- **LaTeX Workshop** (`James-Yu.latex-workshop`) — the only essential one. It gives
  you build commands, PDF preview, SyncTeX, autocomplete, and snippets.
- *(Optional)* **LaTeX Utilities** (`tecosaur.latex-utilities`) — adds live word
  count, formatting helpers. Nice to have, not required.

That's it. LaTeX Workshop auto-detects `latexmk` and works out of the box.

---

## Step 3 — Project layout and the `latexmkrc` file

A minimal project looks like this:

```
my-project/
├── main.tex            ← the root document (\begin{document} ... \end{document})
├── latexmkrc           ← build configuration (see below)
├── references.bib      ← bibliography database (if you cite anything)
├── preamble.tex        ← optional: all your \usepackage lines, \input into main
├── chapters/           ← optional: split content into files, \input them
│   ├── 01_intro.tex
│   └── 02_body.tex
└── build/              ← compiler output goes here (auto-created, git-ignored)
```

Splitting into `preamble.tex` and `chapters/` is just organization — a single
`main.tex` works fine too. The root file pulls pieces in with `\input{...}`:

```latex
\documentclass[11pt,a4paper]{report}
\input{preamble}                 % all \usepackage lines live here
\addbibresource{references.bib}  % register the .bib (biblatex syntax)
\begin{document}
\input{chapters/01_intro}
\input{chapters/02_body}
\printbibliography
\end{document}
```

### The `latexmkrc` file

Create a file named exactly `latexmkrc` (no extension) next to `main.tex`:

```perl
$pdf_mode = 1;        # build a PDF using pdflatex
$out_dir = 'build';   # put all output (PDF + temp files) in build/
```

That's the whole file. What it does:

- `$pdf_mode = 1` → use **pdflatex**. (Use `4` for LuaLaTeX or `5` for XeLaTeX if
  you need system fonts or full Unicode — otherwise leave it at `1`.)
- `$out_dir = 'build'` → keeps the dozen temp files (`.aux`, `.log`, `.bbl`, …)
  out of your source folder. The finished PDF lands at `build/main.pdf`.

`latexmk` automatically figures out **how many times** to run `pdflatex` and
**when to run `biber`** for the bibliography — that's the entire reason to use it
instead of calling `pdflatex` by hand. You never run `biber`/`bibtex` yourself.

> **Bibliography note:** this setup uses **biblatex + biber** (modern, the
> `\addbibresource` / `\printbibliography` commands above). `latexmk` detects this
> and runs `biber` for you. If you instead use the older `\bibliography{}` +
> `\bibitem` style, `latexmk` runs `bibtex` instead — also automatic. Either way,
> you don't think about it.

---

## Step 4 — Tell VS Code to use the build folder

Because output goes to `build/`, point LaTeX Workshop's PDF viewer there. Create
`.vscode/settings.json` in your project root:

```json
{
  "latex-workshop.latex.outDir": "%DIR%/build",
  "latex-workshop.latex.recipe.default": "latexmk",
  "latex-workshop.view.pdf.viewer": "tab",
  "latex-workshop.latex.autoClean.run": "onBuilt",
  "latex-workshop.latex.clean.method": "glob"
}
```

What each line does:

- `latex.outDir` → where the viewer looks for the compiled PDF (matches `$out_dir`).
- `recipe.default: latexmk` → use the `latexmk` recipe, which reads your
  `latexmkrc`. This is LaTeX Workshop's default anyway, but being explicit avoids
  surprises.
- `view.pdf.viewer: tab` → preview the PDF in a VS Code tab beside your source.
  Use `"external"` if you prefer your system PDF reader.
- `autoClean.run: onBuilt` → tidy up stray temp files after each build.

> **Build on save (optional).** Add `"latex-workshop.latex.autoBuild.run": "onSave"`
> to recompile every time you save. Convenient for prose, but on a big document
> the lag can be annoying — many people leave it off and build manually.

---

## Step 5 — Build and view

Open `main.tex`, then either:

- Press **`Ctrl+Alt+B`** (Build LaTeX project), **or**
- Click the green ▶ "Build" button in the top-right, **or**
- Open the **TeX** sidebar icon → *Build LaTeX project*.

The first build is slow if MiKTeX is fetching packages on the fly (let it finish;
approve any MiKTeX install popups). Subsequent builds are fast.

Then **`Ctrl+Alt+V`** opens the PDF preview. Your finished file is `build/main.pdf`.

**SyncTeX** ties the two together:
- `Ctrl+Click` in the PDF → jumps to that line in the source.
- `Ctrl+Alt+J` in the source → jumps to that spot in the PDF.

---

## Step 6 — Git ignore the build artifacts

If the project is under git, add a `.gitignore` so generated files never get
committed:

```gitignore
build/
*.aux
*.bbl
*.bcf
*.blg
*.fdb_latexmk
*.fls
*.lof
*.log
*.lot
*.out
*.run.xml
*.synctex.gz
*.toc
```

The `build/` line covers most of it when `$out_dir = 'build'`; the rest catches
any stragglers if you ever build without the out-dir.

---

## Building from the terminal (no VS Code)

The exact same setup works headless — useful for scripts or CI:

```powershell
latexmk -pdf main.tex     # build (reads latexmkrc, so output → build/)
latexmk -c                # clean temp files, keep the PDF
latexmk -C                # clean everything including the PDF
```

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `latexmk: command not found` | MiKTeX `bin` not on PATH. Reopen terminal; reboot if needed; or add the `...\MiKTeX\miktex\bin\x64` path manually. |
| Build hangs on first run | MiKTeX is downloading packages on the fly. Wait, and approve any install dialogs. Set MiKTeX to install missing packages automatically (Console → Settings). |
| Citations show as `[?]` or `(author?)` | `biber` didn't run or ran before the `.bib` was ready. Do a full clean rebuild: `latexmk -C` then build again. |
| PDF preview is blank / "file not found" | `latex-workshop.latex.outDir` doesn't match `$out_dir` in `latexmkrc`. Make both point to `build`. |
| Changes don't appear | Stale aux files. `latexmk -C`, then rebuild. |
| Wrong engine errors (fonts/Unicode) | Switch `$pdf_mode` in `latexmkrc`: `4` = LuaLaTeX, `5` = XeLaTeX. |

---

## Minimal recap (the short version)

1. Install **MiKTeX** (on-the-fly package install = Yes).
2. Install the **LaTeX Workshop** VS Code extension.
3. Drop a two-line **`latexmkrc`** next to `main.tex`:
   ```perl
   $pdf_mode = 1;
   $out_dir = 'build';
   ```
4. Add a small **`.vscode/settings.json`** pointing the viewer at `build/`.
5. Press **`Ctrl+Alt+B`** to build, **`Ctrl+Alt+V`** to preview.

`latexmk` handles the multi-pass compilation and the bibliography automatically —
that's the whole trick.
