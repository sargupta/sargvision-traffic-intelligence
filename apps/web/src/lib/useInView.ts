"use client";

import { useEffect, useRef, useState } from "react";

/** Reveal-on-scroll that fails open.
 *
 *  The server renders every block fully visible. Only after the client mounts
 *  do we arm the hidden state, so a reader with broken, blocked or slow
 *  JavaScript sees the whole page rather than a blank one. The transition
 *  itself is CSS, not requestAnimationFrame, so a throttled or backgrounded
 *  tab cannot strand content at zero opacity.
 */
export function useInView<T extends HTMLElement>(amount = 0.15) {
  const ref = useRef<T>(null);
  const [armed, setArmed] = useState(false);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Already on screen at mount (above the fold, or a deep link): show it
    // immediately and never hide it, so there is nothing to animate into view.
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.9) {
      setShown(true);
      return;
    }

    setArmed(true);
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold: amount, rootMargin: "0px 0px -6% 0px" },
    );
    io.observe(el);

    // Belt and braces: if the observer never fires for any reason, reveal.
    const failsafe = window.setTimeout(() => setShown(true), 2500);
    return () => {
      io.disconnect();
      window.clearTimeout(failsafe);
    };
  }, [amount]);

  return { ref, hidden: armed && !shown };
}
