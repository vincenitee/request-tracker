import { Component, effect, input, model, output } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Button } from 'primeng/button';
import { Dialog } from 'primeng/dialog';
import { InputText } from 'primeng/inputtext';
import { Message } from 'primeng/message';

/** Create/rename dialog with a single "Name" field (departments and categories). */
@Component({
  selector: 'app-name-dialog',
  imports: [ReactiveFormsModule, Button, Dialog, InputText, Message],
  templateUrl: './name-dialog.html',
  styles: `
    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    label {
      font-weight: 600;
    }
  `,
})
export class NameDialog {
  readonly visible = model(false);
  readonly header = input.required<string>();
  readonly initialName = input('');
  readonly saving = input(false);
  /** A server-side error for the name field (e.g. "already exists"), shown under the input. */
  readonly serverError = input<string | null>(null);
  readonly save = output<string>();

  protected readonly name = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(100)],
  });

  constructor() {
    // Reset the field each time the dialog opens.
    effect(() => {
      if (this.visible()) {
        this.name.reset(this.initialName());
      }
    });
  }

  protected submit(): void {
    if (this.name.invalid) {
      this.name.markAsTouched();
      return;
    }
    this.save.emit(this.name.value.trim());
  }
}
