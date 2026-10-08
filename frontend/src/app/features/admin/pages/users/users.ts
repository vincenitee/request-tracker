import { DatePipe } from '@angular/common';
import { Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormsModule,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Button } from 'primeng/button';
import { Card } from 'primeng/card';
import { Dialog } from 'primeng/dialog';
import { IconField } from 'primeng/iconfield';
import { InputIcon } from 'primeng/inputicon';
import { InputText } from 'primeng/inputtext';
import { Message } from 'primeng/message';
import { Password } from 'primeng/password';
import { Select } from 'primeng/select';
import { TableLazyLoadEvent, TableModule } from 'primeng/table';
import { Tag } from 'primeng/tag';
import { ToggleSwitch } from 'primeng/toggleswitch';
import { catchError, debounceTime, distinctUntilChanged, map, of, Subject, switchMap, tap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { TableSkeleton } from '../../../../shared/components/table-skeleton/table-skeleton';
import { Role } from '../../../../shared/models/user.model';
import { applyServerErrors } from '../../../../shared/utils/api-errors';
import { notifyError } from '../../../../shared/utils/notify';
import { AdminUser, Department, ROLE_OPTIONS, UserQuery, UserWrite } from '../../models/admin.model';
import { DepartmentsService } from '../../services/departments.service';
import { UsersService } from '../../services/users.service';

const PAGE_SIZE = 10;

/** Mirrors the server rule: a reviewer must belong to a department. */
function reviewerNeedsDepartment(group: AbstractControl): ValidationErrors | null {
  const role = group.get('role')?.value;
  const department = group.get('department')?.value;
  return role === 'reviewer' && !department ? { reviewerNeedsDepartment: true } : null;
}

function passwordsMatch(group: AbstractControl): ValidationErrors | null {
  return group.get('password')?.value === group.get('confirm')?.value ? null : { mismatch: true };
}

@Component({
  selector: 'app-users',
  imports: [
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    Button,
    Card,
    Dialog,
    IconField,
    InputIcon,
    InputText,
    Message,
    Password,
    Select,
    TableModule,
    Tag,
    ToggleSwitch,
    EmptyState,
    PageHeader,
    TableSkeleton,
  ],
  templateUrl: './users.html',
  styleUrl: './users.scss',
})
export class Users implements OnInit {
  private readonly usersService = inject(UsersService);
  private readonly departmentsService = inject(DepartmentsService);
  private readonly confirmation = inject(ConfirmationService);
  private readonly messages = inject(MessageService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly me = inject(AuthService).currentUser;

  protected readonly pageSize = PAGE_SIZE;
  protected readonly roleOptions = ROLE_OPTIONS;
  protected readonly activeOptions = [
    { label: 'Active', value: true },
    { label: 'Inactive', value: false },
  ];

  // --- list state ---
  protected readonly users = signal<AdminUser[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly firstLoad = signal(true);
  protected readonly first = signal(0);
  protected readonly departments = signal<Department[]>([]);

  protected readonly search = signal('');
  protected readonly role = signal<Role | null>(null);
  protected readonly department = signal<number | null>(null);
  protected readonly isActive = signal<boolean | null>(null);
  protected readonly hasFilters = computed(() => !!(this.search() || this.role() || this.department() || this.isActive() !== null));
  private ordering = 'username';

  private readonly reload$ = new Subject<void>();
  private readonly searchInput$ = new Subject<string>();

  // --- create / edit dialog ---
  protected readonly formOpen = signal(false);
  protected readonly editing = signal<AdminUser | null>(null);
  protected readonly saving = signal(false);
  protected readonly form = this.fb.group(
    {
      username: ['', [Validators.required, Validators.maxLength(150), Validators.pattern(/^[\w.@+-]+$/)]],
      first_name: ['', Validators.maxLength(150)],
      last_name: ['', Validators.maxLength(150)],
      email: ['', [Validators.email, Validators.maxLength(254)]],
      role: ['staff' as Role, Validators.required],
      department: this.fb.control<number | null>(null),
      is_active: [true],
      password: [''],
    },
    { validators: reviewerNeedsDepartment },
  );

  // --- reset password dialog ---
  protected readonly resetFor = signal<AdminUser | null>(null);
  protected readonly resetting = signal(false);
  protected readonly resetForm = this.fb.group(
    { password: ['', [Validators.required, Validators.minLength(8)]], confirm: ['', Validators.required] },
    { validators: passwordsMatch },
  );

  ngOnInit(): void {
    this.reload$
      .pipe(
        map(() => this.currentQuery()),
        tap(() => this.loading.set(true)),
        switchMap((query) =>
          this.usersService.list(query).pipe(
            catchError((error) => {
              notifyError(this.messages, 'Could not load users', error);
              return of({ count: 0, next: null, previous: null, results: [] as AdminUser[] });
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.users.set(page.results);
        this.total.set(page.count);
        this.loading.set(false);
        this.firstLoad.set(false);
      });

    this.searchInput$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe((term) => {
        this.search.set(term.trim());
        this.resetToFirstPage();
      });

    this.departmentsService.list().subscribe({
      next: (list) => this.departments.set(list),
      error: (error) => notifyError(this.messages, 'Could not load departments', error),
    });
  }

  // --- list ---

  protected onLazyLoad(event: TableLazyLoadEvent): void {
    this.first.set(event.first ?? 0);
    const field = Array.isArray(event.sortField) ? event.sortField[0] : event.sortField;
    if (field) {
      this.ordering = (event.sortOrder === -1 ? '-' : '') + field;
    }
    this.reload$.next();
  }

  protected onSearchInput(term: string): void {
    this.searchInput$.next(term);
  }

  protected setFilter<T>(filter: { set(value: T): void }, value: T): void {
    filter.set(value);
    this.resetToFirstPage();
  }

  protected isMe(user: AdminUser): boolean {
    return user.id === this.me()?.id;
  }

  // --- create / edit ---

  protected openCreate(): void {
    this.editing.set(null);
    this.form.reset({ username: '', first_name: '', last_name: '', email: '', role: 'staff', department: null, is_active: true, password: '' });
    this.form.controls.username.enable();
    this.form.controls.password.setValidators([Validators.required, Validators.minLength(8)]);
    this.form.controls.password.updateValueAndValidity();
    this.formOpen.set(true);
  }

  protected openEdit(user: AdminUser): void {
    this.editing.set(user);
    this.form.reset({
      username: user.username,
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      role: user.role,
      department: user.department?.id ?? null,
      is_active: user.is_active,
      password: '',
    });
    this.form.controls.password.clearValidators(); // passwords change through "Reset password" only
    this.form.controls.password.updateValueAndValidity();
    this.formOpen.set(true);
  }

  protected showError(name: keyof typeof this.form.controls): boolean {
    const control = this.form.controls[name];
    return control.invalid && control.touched;
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const editing = this.editing();
    const { password, ...fields } = this.form.getRawValue();
    const body: UserWrite = editing ? fields : { ...fields, password };

    this.saving.set(true);
    const call = editing ? this.usersService.update(editing.id, body) : this.usersService.create(body);
    call.subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.formOpen.set(false);
        this.messages.add({ severity: 'success', summary: editing ? 'User updated' : 'User created', detail: saved.username });
        this.reload$.next();
      },
      error: (error) => {
        this.saving.set(false);
        // Field errors (e.g. "username already exists", self-deactivation) go on the form; the rest in a toast.
        const leftover = applyServerErrors(this.form, error);
        notifyError(this.messages, 'Could not save user', error, leftover ?? undefined);
      },
    });
  }

  // --- activate / deactivate ---

  protected confirmToggleActive(user: AdminUser, event: Event): void {
    const activate = !user.is_active;
    this.confirmation.confirm({
      target: event.target as EventTarget,
      header: activate ? 'Activate user' : 'Deactivate user',
      message: activate
        ? `Allow ${user.username} to sign in again?`
        : `${user.username} will no longer be able to sign in. Their requests and history are kept.`,
      icon: activate ? 'pi pi-user-plus' : 'pi pi-user-minus',
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptButtonProps: { label: activate ? 'Activate' : 'Deactivate', severity: activate ? 'success' : 'danger' },
      accept: () =>
        this.usersService.update(user.id, { is_active: activate }).subscribe({
          next: () => {
            this.messages.add({ severity: 'success', summary: activate ? 'User activated' : 'User deactivated', detail: user.username });
            this.reload$.next();
          },
          // e.g. "You cannot deactivate your own account." / "The last active admin cannot be deactivated or demoted."
          error: (error) => notifyError(this.messages, activate ? 'Could not activate user' : 'Could not deactivate user', error),
        }),
    });
  }

  // --- reset password ---

  protected openReset(user: AdminUser): void {
    this.resetForm.reset({ password: '', confirm: '' });
    this.resetFor.set(user);
  }

  protected closeReset(): void {
    this.resetFor.set(null);
  }

  protected resetPassword(): void {
    const user = this.resetFor();
    if (!user || this.resetForm.invalid) {
      this.resetForm.markAllAsTouched();
      return;
    }
    this.resetting.set(true);
    this.usersService.setPassword(user.id, this.resetForm.controls.password.value).subscribe({
      next: () => {
        this.resetting.set(false);
        this.resetFor.set(null);
        this.messages.add({ severity: 'success', summary: 'Password reset', detail: `Share the new password with ${user.username} securely.` });
      },
      error: (error) => {
        this.resetting.set(false);
        const leftover = applyServerErrors(this.resetForm, error);
        notifyError(this.messages, 'Could not reset password', error, leftover ?? undefined);
      },
    });
  }

  private resetToFirstPage(): void {
    this.first.set(0);
    this.reload$.next();
  }

  private currentQuery(): UserQuery {
    return {
      page: Math.floor(this.first() / PAGE_SIZE) + 1,
      ordering: this.ordering,
      search: this.search(),
      role: this.role(),
      department: this.department(),
      isActive: this.isActive(),
    };
  }
}
