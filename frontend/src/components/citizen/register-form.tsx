"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "./form-field";
import { StatusAlert } from "./status-alert";
import { registerCitizen } from "@/lib/citizen/api";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import type {
  CitizenIdentityKind,
  CitizenRegistrationRequest,
  CitizenRegistrationResponse,
} from "@/lib/citizen/types";

type RegistrationValues = {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
  dateOfBirth: string;
  gender: string;
  bloodGroup: string;
  address: string;
  identityKind: CitizenIdentityKind;
  identityNumber: string;
};

type RegistrationErrors = Partial<Record<keyof RegistrationValues, string>>;

const initialValues: RegistrationValues = {
  firstName: "",
  lastName: "",
  email: "",
  password: "",
  confirmPassword: "",
  dateOfBirth: "",
  gender: "",
  bloodGroup: "",
  address: "",
  identityKind: "NID",
  identityNumber: "",
};

export function localCalendarDate(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return year + "-" + month + "-" + day;
}

export function validateCitizenRegistration(
  values: RegistrationValues,
): RegistrationErrors {
  const errors: RegistrationErrors = {};

  if (!values.firstName.trim()) errors.firstName = "First name is required.";
  if (!values.lastName.trim()) errors.lastName = "Last name is required.";
  if (!/^\S+@\S+\.\S+$/.test(values.email.trim())) {
    errors.email = "Enter a valid email address.";
  }
  if (values.password.length < 8) {
    errors.password = "Use at least 8 characters.";
  } else if (values.password.length > 128) {
    errors.password = "Password cannot exceed 128 characters.";
  }
  if (values.password !== values.confirmPassword) {
    errors.confirmPassword = "Passwords do not match.";
  }
  if (!values.dateOfBirth) {
    errors.dateOfBirth = "Date of birth is required.";
  } else if (values.dateOfBirth > localCalendarDate()) {
    errors.dateOfBirth = "Date of birth cannot be in the future.";
  }
  if (!values.gender) errors.gender = "Select a gender.";

  const identityNumber = values.identityNumber.trim();
  if (!identityNumber) {
    errors.identityNumber =
      values.identityKind === "NID"
        ? "National ID is required."
        : "Birth Certificate Number is required.";
  } else if (
    values.identityKind === "NID" &&
    identityNumber.length > 32
  ) {
    errors.identityNumber = "NID cannot exceed 32 characters.";
  } else if (
    values.identityKind === "BCN" &&
    identityNumber.length > 64
  ) {
    errors.identityNumber =
      "Birth Certificate Number cannot exceed 64 characters.";
  }

  return errors;
}

function registrationPayload(
  values: RegistrationValues,
): CitizenRegistrationRequest {
  const baseRequest = {
    address: values.address.trim() || null,
    blood_group: values.bloodGroup || null,
    date_of_birth: values.dateOfBirth,
    email: values.email.trim().toLowerCase(),
    first_name: values.firstName.trim(),
    gender: values.gender,
    last_name: values.lastName.trim(),
    password: values.password,
  };

  return values.identityKind === "NID"
    ? {
        ...baseRequest,
        nid_number: values.identityNumber.trim(),
      }
    : {
        ...baseRequest,
        birth_certificate_number: values.identityNumber.trim(),
      };
}

export function CitizenRegisterForm({
  onRegistered,
  registerAction = registerCitizen,
}: {
  onRegistered?: (response: CitizenRegistrationResponse) => void;
  registerAction?: (
    request: CitizenRegistrationRequest,
  ) => Promise<CitizenRegistrationResponse>;
}) {
  const router = useRouter();
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<RegistrationErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateValue = <Field extends keyof RegistrationValues>(
    field: Field,
    value: RegistrationValues[Field],
  ) => {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setApiError(null);
  };

  const selectIdentity = (identityKind: CitizenIdentityKind) => {
    setValues((current) => ({
      ...current,
      identityKind,
      identityNumber: "",
    }));
    setErrors((current) => ({ ...current, identityNumber: undefined }));
    setApiError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validateCitizenRegistration(values);

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      setApiError("Please review the highlighted fields.");
      return;
    }

    setIsSubmitting(true);
    setApiError(null);

    try {
      const response = await registerAction(registrationPayload(values));
      if (onRegistered) {
        onRegistered(response);
      } else {
        router.replace("/citizen/login?registered=1");
      }
    } catch (error) {
      setApiError(
        citizenErrorMessage(
          error,
          "We could not create your account. Please review your information and try again.",
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const identityLabel =
    values.identityKind === "NID" ? "National ID" : "Birth Certificate Number";
  const identityHint =
    values.identityKind === "NID"
      ? "Enter the value exactly as shown on your NID, up to 32 characters."
      : "Enter the value exactly as shown on your birth certificate, up to 64 characters.";

  return (
    <div>
      <div className="border-b border-slate-200 pb-7">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">New citizen account</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Create your HealthLink identity</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Use exactly one national identity document. You&apos;ll sign in after account creation.
        </p>
      </div>

      <form className="mt-8 space-y-8" noValidate onSubmit={handleSubmit}>
        {apiError ? <StatusAlert message={apiError} /> : null}

        <fieldset>
          <legend className="text-sm font-bold text-slate-950">Choose one identity document</legend>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Only the selected document is submitted.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(["NID", "BCN"] as const).map((kind) => {
              const selected = values.identityKind === kind;
              const label = kind === "NID" ? "NID" : "Birth Certificate Number";
              return (
                <label
                  className={
                    "cursor-pointer rounded-2xl border p-4 transition focus-within:ring-4 focus-within:ring-teal-100 " +
                    (selected
                      ? "border-teal-600 bg-teal-50 shadow-sm"
                      : "border-slate-200 bg-white hover:border-slate-300")
                  }
                  key={kind}
                >
                  <span className="flex items-center gap-3">
                    <input
                      checked={selected}
                      className="size-4 accent-teal-700"
                      name="identity-kind"
                      onChange={() => selectIdentity(kind)}
                      type="radio"
                      value={kind}
                    />
                    <span>
                      <span className="block text-sm font-bold text-slate-900">{label}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        {kind === "NID" ? "For citizens with a National ID" : "For citizens without an NID"}
                      </span>
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <FormField
          error={errors.identityNumber}
          hint={identityHint}
          htmlFor="identity-number"
          label={identityLabel}
          required
        >
          <input
            aria-describedby={errors.identityNumber ? "identity-number-error" : "identity-number-hint"}
            aria-invalid={Boolean(errors.identityNumber)}
            autoComplete="off"
            className={citizenInputClassName}
            id="identity-number"
            inputMode="numeric"
            maxLength={values.identityKind === "NID" ? 32 : 64}
            onChange={(event) => updateValue("identityNumber", event.target.value)}
            placeholder={values.identityKind === "NID" ? "Enter your NID" : "Enter your BCN"}
            required
            value={values.identityNumber}
          />
        </FormField>

        <div>
          <h3 className="text-sm font-bold text-slate-950">Personal details</h3>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <FormField error={errors.firstName} htmlFor="first-name" label="First name" required>
              <input
                aria-describedby={errors.firstName ? "first-name-error" : undefined}
                aria-invalid={Boolean(errors.firstName)}
                autoComplete="given-name"
                className={citizenInputClassName}
                id="first-name"
                maxLength={100}
                onChange={(event) => updateValue("firstName", event.target.value)}
                required
                value={values.firstName}
              />
            </FormField>
            <FormField error={errors.lastName} htmlFor="last-name" label="Last name" required>
              <input
                aria-describedby={errors.lastName ? "last-name-error" : undefined}
                aria-invalid={Boolean(errors.lastName)}
                autoComplete="family-name"
                className={citizenInputClassName}
                id="last-name"
                maxLength={100}
                onChange={(event) => updateValue("lastName", event.target.value)}
                required
                value={values.lastName}
              />
            </FormField>
            <FormField error={errors.dateOfBirth} htmlFor="date-of-birth" label="Date of birth" required>
              <input
                aria-describedby={errors.dateOfBirth ? "date-of-birth-error" : undefined}
                aria-invalid={Boolean(errors.dateOfBirth)}
                className={citizenInputClassName}
                id="date-of-birth"
                max={localCalendarDate()}
                onChange={(event) => updateValue("dateOfBirth", event.target.value)}
                required
                type="date"
                value={values.dateOfBirth}
              />
            </FormField>
            <FormField error={errors.gender} htmlFor="gender" label="Gender" required>
              <select
                aria-describedby={errors.gender ? "gender-error" : undefined}
                aria-invalid={Boolean(errors.gender)}
                className={citizenInputClassName}
                id="gender"
                onChange={(event) => updateValue("gender", event.target.value)}
                required
                value={values.gender}
              >
                <option value="">Select gender</option>
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
                <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
              </select>
            </FormField>
            <FormField htmlFor="blood-group" label="Blood group">
              <select
                className={citizenInputClassName}
                id="blood-group"
                onChange={(event) => updateValue("bloodGroup", event.target.value)}
                value={values.bloodGroup}
              >
                <option value="">Not specified</option>
                {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((group) => (
                  <option key={group} value={group}>{group}</option>
                ))}
              </select>
            </FormField>
            <FormField className="sm:col-span-2" htmlFor="address" label="Address">
              <textarea
                className={citizenInputClassName + " min-h-24 py-3"}
                id="address"
                onChange={(event) => updateValue("address", event.target.value)}
                placeholder="Current address (optional)"
                value={values.address}
              />
            </FormField>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-bold text-slate-950">Account security</h3>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <FormField error={errors.email} htmlFor="email" label="Email address" required>
              <input
                aria-describedby={errors.email ? "email-error" : undefined}
                aria-invalid={Boolean(errors.email)}
                autoComplete="email"
                className={citizenInputClassName}
                id="email"
                maxLength={320}
                onChange={(event) => updateValue("email", event.target.value)}
                required
                type="email"
                value={values.email}
              />
            </FormField>
            <div className="hidden sm:block" />
            <FormField error={errors.password} hint="Use at least 8 characters." htmlFor="password" label="Password" required>
              <input
                aria-describedby={errors.password ? "password-error" : "password-hint"}
                aria-invalid={Boolean(errors.password)}
                autoComplete="new-password"
                className={citizenInputClassName}
                id="password"
                maxLength={128}
                onChange={(event) => updateValue("password", event.target.value)}
                required
                type="password"
                value={values.password}
              />
            </FormField>
            <FormField error={errors.confirmPassword} htmlFor="confirm-password" label="Confirm password" required>
              <input
                aria-describedby={errors.confirmPassword ? "confirm-password-error" : undefined}
                aria-invalid={Boolean(errors.confirmPassword)}
                autoComplete="new-password"
                className={citizenInputClassName}
                id="confirm-password"
                maxLength={128}
                onChange={(event) => updateValue("confirmPassword", event.target.value)}
                required
                type="password"
                value={values.confirmPassword}
              />
            </FormField>
          </div>
        </div>

        <div className="border-t border-slate-200 pt-6">
          <button
            className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-teal-700 px-6 text-sm font-bold text-white shadow-lg shadow-teal-900/15 transition hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-wait disabled:opacity-65 sm:w-auto"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating account…" : "Create citizen account"}
          </button>
          <p className="mt-5 text-sm text-slate-600">
            Already registered?{" "}
            <Link className="font-bold text-teal-700 hover:text-teal-900" href="/citizen/login">
              Sign in to HealthLink
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}
