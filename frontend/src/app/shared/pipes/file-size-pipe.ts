import { Pipe, PipeTransform } from '@angular/core';

const UNITS = ['B', 'KB', 'MB', 'GB'];

/** 1536 -> "1.5 KB", 5242880 -> "5 MB". */
@Pipe({ name: 'fileSize' })
export class FileSizePipe implements PipeTransform {
  transform(bytes: number | null | undefined): string {
    if (bytes == null || bytes < 0) {
      return '';
    }
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < UNITS.length - 1) {
      value /= 1024;
      unit++;
    }
    const rounded = unit === 0 ? value : Math.round(value * 10) / 10;
    return `${rounded} ${UNITS[unit]}`;
  }
}
