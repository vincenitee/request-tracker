import { formatDate } from '@angular/common';
import { inject, LOCALE_ID, Pipe, PipeTransform } from '@angular/core';

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
];
const RELATIVE_LIMIT_SECONDS = 7 * 86_400;

/**
 * "just now", "5 minutes ago", "3 days ago" for the last 7 days; an absolute date after that.
 * Pure, so it updates on change detection rather than ticking live. Pair with [title] for the exact time.
 */
@Pipe({ name: 'relativeDate' })
export class RelativeDatePipe implements PipeTransform {
  private readonly locale = inject(LOCALE_ID);
  private readonly rtf = new Intl.RelativeTimeFormat(this.locale, { numeric: 'auto' });

  transform(value: string | Date | null | undefined, absoluteFormat = 'mediumDate'): string {
    if (!value) {
      return '';
    }
    const date = new Date(value);
    const secondsAgo = (Date.now() - date.getTime()) / 1000;

    if (secondsAgo < 0 || secondsAgo >= RELATIVE_LIMIT_SECONDS) {
      return formatDate(date, absoluteFormat, this.locale);
    }
    if (secondsAgo < 45) {
      return 'just now';
    }
    for (const [unit, size] of UNITS) {
      if (secondsAgo >= size) {
        return this.rtf.format(-Math.floor(secondsAgo / size), unit);
      }
    }
    return this.rtf.format(-Math.max(1, Math.round(secondsAgo / 60)), 'minute');
  }
}
