function requireElement(id: string): HTMLElement {
  const element = document.getElementById(id);
  if (element === null) throw new Error(`index.html is missing the #${id} element.`);
  return element;
}

export type Poster = {
  /** Fraction 0..1. */
  readonly setProgress: (fraction: number) => void;
  readonly setMessage: (text: string) => void;
  /** Removes the poster (fades out unless the visitor prefers reduced motion). */
  readonly hide: () => void;
};

const FADE_MS = 400;

/**
 * The loading poster is plain HTML in index.html, so its text is the first thing painted (and the
 * largest-contentful-paint candidate: a `<canvas>` is not one). This only updates it. It is
 * `aria-hidden`; screen readers get the same messages from `#status`.
 */
export function createPoster(): Poster {
  const poster = requireElement("poster");
  const message = requireElement("poster-message");
  const bar = requireElement("poster-bar");
  let hidden = false;
  return {
    setProgress: (fraction) => {
      if (hidden) return;
      bar.style.transform = `scaleX(${Math.min(Math.max(fraction, 0), 1)})`;
    },
    setMessage: (text) => {
      if (!hidden) message.textContent = text;
    },
    hide: () => {
      if (hidden) return;
      hidden = true;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        poster.hidden = true;
        return;
      }
      poster.dataset.state = "done";
      window.setTimeout(() => {
        poster.hidden = true;
      }, FADE_MS);
    },
  };
}
