# DESIGN_TOKENS.md — Orano Design System & Motion Mapping for RimeRx

Extracted from live inspection of [Orano Group](https://www.orano.group/en) computed styles and CSS assets (`main.css` and `index.css`).

---

## 1. Color Palette

| Token Name | Hex / Value | Usage in Orano | Mapping in RimeRx |
| :--- | :--- | :--- | :--- |
| **Primary Accent** | `#ffe600` | Orano signature bright yellow used for CTAs, active lines, highlights, tag etiquettes, quote marks. | Primary CTA buttons, metric highlights ("DELTA"), active step indicators, focus rings, status badges ("SYSTEM OK"). |
| **Hover Accent** | `#e5b700` | Hover state for primary yellow elements. | Hover state for primary action buttons. |
| **Deep Dark Background** | `#080c14` / `#000000` | Footer, mobile drawer headers, high-contrast dark sections. | Page main background (`body`), top header, modal backdrop. |
| **Card Surface** | `#111622` / `#161c28` | Content panels, drawers, white/dark container surfaces. | Metric cards, test selector panel, audio containers, modal body. |
| **Border Muted** | `rgba(255, 255, 255, 0.08)` / `#1e293b` | Divider lines, card outlines, subtle grid dividers. | Card borders, section dividers, input borders. |
| **Secondary / Brand Accent** | `#00677f` | Secondary dark teal/cyan used in Orano forms and active chip tags. | Secondary accents, subtle background tints, process step badges. |
| **Text Primary** | `#ffffff` / `#f4f4f5` | Main body text on dark sections. | Page title, body copy, card headings. |
| **Text Muted** | `#94a3b8` / `#c6c6c6` | Eyebrow labels, timestamps, metadata. | Eyebrows, timestamps, subtext, character count. |
| **Text On Primary CTA** | `#000000` | High-contrast dark text inside yellow buttons and tags. | Text on yellow `#ffe600` buttons and badges. |

---

## 2. Typography

| Role | Font Family | Weight / Style | Letter-Spacing & Scale |
| :--- | :--- | :--- | :--- |
| **Headings (H1, H2, H3)** | `'Nunito Sans'`, `sans-serif` | 700 / Bold | Clean, geometric sans-serif. Left-accent border (`3px solid #ffe600`). |
| **Body & UI Controls** | `'Open Sans'`, `'Inter'`, `sans-serif` | 400 (Regular), 600 (Semibold) | Standard leading, crisp legibility for prescription texts. |
| **Technical Metrics / Code** | `'JetBrains Mono'`, `monospace` | 500 / 700 Bold | Tabular figures for WER, PER, CER, MOS, timestamps, diffs. |
| **Eyebrows & Labels** | `'Nunito Sans'`, `sans-serif` | 700 Bold, Uppercase | `letter-spacing: 0.1em` (`tracking-wider`), uppercase tracking (e.g. `PROCESS STEP 01`). |

---

## 3. Spacing & Layout Rhythm

- **Max Content Width**: `1280px` (`max-w-7xl` / `container`), centered with `24px` (`px-6`) padding.
- **Section Padding**: `24px` to `32px` (`p-6 sm:p-8`) internal card padding with generous gap spacing (`gap-6`).
- **Section Divider Accent**: Left-border line (`border-left: 3px solid #ffe600`) or top/bottom accent bar (`width: 30px; height: 3px; background-color: #ffe600`).
- **Card Corners**: Restrained `12px` to `16px` border-radius (`rounded-xl` / `rounded-2xl`) with subtle 1px border.

---

## 4. Component Patterns

- **Primary Action Buttons**: `#ffe600` background, `#000000` bold text, uppercase font tracking, yellow glow & lift on hover (`hover:-translate-y-0.5 hover:shadow-xl hover:shadow-[#ffe600]/20`).
- **Secondary Buttons**: Dark surface (`#161c28`) with thin yellow/gray border (`border border-[#ffe600]/40`), `#ffe600` text, hover background shift & subtle scale.
- **Status Badges ("SYSTEM OK", "SEMANTICS PRESERVED")**: Pill/tag shape with crisp `#ffe600` background & black text, or dark badge with `#ffe600` border & pulsing dot.
- **Audio Players**: Custom dark controls matching `#111622` background with `#ffe600` accent highlights.
- **Results Table**: Dark rows with subtle borders (`border-b border-white/5`), uppercase header row, highlighted metric values.

---

## 5. Enhanced Motion System (Step 2b Specifications)

- **Easing Curve**: Standardized premium `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out feel) for responsive, non-sluggish motion (150ms - 400ms duration).
- **Page Load / Scroll Entrance**: Native `IntersectionObserver` triggering staggered fade-in & slide-up (`.reveal-on-scroll`) as elements scroll into view.
- **Numeric Count-Up Animations**: `requestAnimationFrame`-driven smooth count-up for WER, PER, CER, MOS, Delta score, and recall percentages from 0 to final target.
- **State Change Transitions**: Skeleton shimmer pulse during audio synthesis & ASR checks; smooth cross-fades when results load.
- **Blind Test Reveal Payoff**: Blur-to-sharp scale+fade animation (`@keyframes reveal-payoff`) when identities are revealed.
- **Interactive Control Transforms**: Hover scale/lift (`-translate-y-0.5`) with shadow expansion; active button depression (`translate-y-0`); spinner rotation on async calls.
- **Stress Test Entity Stagger**: Sequential pop-in animation (`@keyframes pop-in`) for critical entity recall checklist items.
- **Reduced Motion Fallback**: `@media (prefers-reduced-motion: reduce)` wrapping all animations to disable/shorten motion for accessibility requests.
