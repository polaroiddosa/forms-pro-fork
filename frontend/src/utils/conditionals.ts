import {
  ConditionalLogic,
  ConditionalOperators,
  Condition,
  Actions,
} from "@/types/conditional-render.types";
import { FormField, Fieldtype } from "@/types/formfield";
import { getFieldTypeDef } from "@/config/fieldTypes";

/**
 * Parse conditional_logic string into ConditionalLogic object
 */
export function parseConditionalLogic(
  conditionalLogic: string | undefined | null
): ConditionalLogic | null {
  if (!conditionalLogic || conditionalLogic.trim() === "") {
    return null;
  }

  try {
    return JSON.parse(conditionalLogic) as ConditionalLogic;
  } catch (e) {
    console.error("Failed to parse conditional_logic:", e);
    return null;
  }
}

/**
 * Get the value of a field from form data, handling different field types
 */
function getFieldValue(
  fieldValue: any,
  fieldType: string
): string | number | boolean | null {
  if (fieldValue === null || fieldValue === undefined || fieldValue === "") {
    return null;
  }

  const typeDef = getFieldTypeDef(fieldType as Fieldtype);

  if (typeDef?.isBoolean) {
    return Boolean(fieldValue);
  }

  // Handle number fields
  if (fieldType === Fieldtype.NUMBER) {
    const num = Number(fieldValue);
    return isNaN(num) ? null : num;
  }

  // Handle string fields
  return String(fieldValue);
}

/**
 * Normalize values for comparison (convert to strings for most comparisons)
 */
function normalizeValue(value: any): string | number | boolean | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    return value;
  }
  return String(value).trim();
}

/**
 * Evaluate a single condition against form field values
 */
function evaluateCondition(
  condition: Condition,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  const { fieldname, operator, value } = condition;

  // Get the field definition to understand its type
  const field = allFields.find((f) => f.fieldname === fieldname);
  if (!field) {
    console.warn(`Field ${fieldname} not found in form fields`);
    return false;
  }

  // Multiple choice answers are arrays: compare by membership, not by the
  // comma-joined string (so "Art" does not match "Artisan").
  const rawValue = formValues[fieldname];
  if (Array.isArray(rawValue)) {
    const items = rawValue.map((v) => String(v).trim());
    const wanted = String(normalizeValue(value) ?? "");
    switch (operator) {
      case ConditionalOperators.Is:
      case ConditionalOperators.Contains:
        return items.includes(wanted);
      case ConditionalOperators.IsNot:
      case ConditionalOperators.DoesNotContain:
        return !items.includes(wanted);
      case ConditionalOperators.IsEmpty:
        return items.length === 0;
      case ConditionalOperators.IsNotEmpty:
      case ConditionalOperators.IsSet:
        return items.length > 0;
      default:
        break;
    }
  }

  const fieldValue = getFieldValue(rawValue, field.fieldtype);
  const conditionValue = normalizeValue(value);
  const normalizedFieldValue = normalizeValue(fieldValue);

  switch (operator) {
    case ConditionalOperators.Is:
      return normalizedFieldValue === conditionValue;

    case ConditionalOperators.IsNot:
      return normalizedFieldValue !== conditionValue;

    case ConditionalOperators.IsEmpty:
      return (
        normalizedFieldValue === null ||
        normalizedFieldValue === "" ||
        normalizedFieldValue === undefined
      );

    case ConditionalOperators.IsNotEmpty:
      return (
        normalizedFieldValue !== null &&
        normalizedFieldValue !== "" &&
        normalizedFieldValue !== undefined
      );

    case ConditionalOperators.IsSet:
      return (
        normalizedFieldValue !== null && normalizedFieldValue !== undefined
      );

    case ConditionalOperators.Contains:
      if (normalizedFieldValue === null) return false;
      return String(normalizedFieldValue)
        .toLowerCase()
        .includes(String(conditionValue).toLowerCase());

    case ConditionalOperators.DoesNotContain:
      if (normalizedFieldValue === null) return true;
      return !String(normalizedFieldValue)
        .toLowerCase()
        .includes(String(conditionValue).toLowerCase());

    case ConditionalOperators.IsLessThan:
      if (
        typeof normalizedFieldValue === "number" &&
        typeof conditionValue === "number"
      ) {
        return normalizedFieldValue < conditionValue;
      }
      return false;

    case ConditionalOperators.IsLessThanOrEqualTo:
      if (
        typeof normalizedFieldValue === "number" &&
        typeof conditionValue === "number"
      ) {
        return normalizedFieldValue <= conditionValue;
      }
      return false;

    case ConditionalOperators.IsGreaterThan:
      if (
        typeof normalizedFieldValue === "number" &&
        typeof conditionValue === "number"
      ) {
        return normalizedFieldValue > conditionValue;
      }
      return false;

    case ConditionalOperators.IsGreaterThanOrEqualTo:
      if (
        typeof normalizedFieldValue === "number" &&
        typeof conditionValue === "number"
      ) {
        return normalizedFieldValue >= conditionValue;
      }
      return false;

    case ConditionalOperators.StartsWith:
      if (normalizedFieldValue === null) return false;
      return String(normalizedFieldValue)
        .toLowerCase()
        .startsWith(String(conditionValue).toLowerCase());

    case ConditionalOperators.DoesNotStartWith:
      if (normalizedFieldValue === null) return true;
      return !String(normalizedFieldValue)
        .toLowerCase()
        .startsWith(String(conditionValue).toLowerCase());

    case ConditionalOperators.EndsWith:
      if (normalizedFieldValue === null) return false;
      return String(normalizedFieldValue)
        .toLowerCase()
        .endsWith(String(conditionValue).toLowerCase());

    case ConditionalOperators.DoesNotEndWith:
      if (normalizedFieldValue === null) return true;
      return !String(normalizedFieldValue)
        .toLowerCase()
        .endsWith(String(conditionValue).toLowerCase());

    default:
      console.warn(`Unknown operator: ${operator}`);
      return false;
  }
}

/**
 * Evaluate all conditions in a ConditionalLogic object
 * Currently supports AND logic (all conditions must be true)
 * TODO: Add support for OR logic if needed
 */
function evaluateConditions(
  conditionalLogic: ConditionalLogic,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  if (
    !conditionalLogic.conditions ||
    conditionalLogic.conditions.length === 0
  ) {
    return false;
  }

  // All conditions must be true (AND logic)
  return conditionalLogic.conditions.every((condition) =>
    evaluateCondition(condition, formValues, allFields)
  );
}

/**
 * Determine if a field should be visible based on:
 * 1. The field's `hidden` property (base state)
 * 2. Conditional logic rules defined on other fields that target this field
 *
 * Visibility logic:
 * - If field.hidden === true, field starts as hidden
 * - If field.hidden === false or undefined, field starts as visible,
 *   EXCEPT when it is the target of a "Show Field" rule: then it starts hidden
 * - Conditional logic can override the base state:
 *   - "Show Field" action can make a hidden field visible
 *   - "Hide Field" action can make a visible field hidden
 * - If no conditional logic applies, the base hidden state is used
 */
export function shouldFieldBeVisible(
  field: FormField,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  // Find all conditional logic rules that target this field
  const targetingRules: ConditionalLogic[] = [];

  allFields.forEach((otherField) => {
    if (!otherField.conditional_logic) return;

    const logic = parseConditionalLogic(otherField.conditional_logic);
    if (logic && logic.target_field === field.fieldname) {
      targetingRules.push(logic);
    }
  });

  // Base visibility (contract C6, mirrored in the Python validator):
  // - the target of a "Show Field" rule is hidden until the rule's conditions
  //   are met, even when its own Hidden box is not ticked;
  // - the target of a "Hide Field" rule stays visible until its conditions are met.
  const hasShowTarget = targetingRules.some(
    (rule) => rule.action === Actions.ShowField
  );
  const baseIsVisible = hasShowTarget ? false : !field.hidden;

  // If no rules target this field, use the base hidden state
  if (targetingRules.length === 0) {
    return baseIsVisible;
  }

  // Check each rule
  let hasShowRule = false;
  let hasHideRule = false;

  for (const rule of targetingRules) {
    const conditionsMet = evaluateConditions(rule, formValues, allFields);

    if (conditionsMet) {
      if (rule.action === Actions.ShowField) {
        hasShowRule = true;
      } else if (rule.action === Actions.HideField) {
        hasHideRule = true;
      }
    }
  }

  // Conditional logic overrides base state:
  // - "Show Field" action can override hidden state (make it visible)
  if (hasShowRule) {
    return true;
  }

  // - "Hide Field" action can override visible state (make it hidden)
  if (hasHideRule) {
    return false;
  }

  // If no conditional rules are met, use the base hidden state
  return baseIsVisible;
}

/**
 * Determine if a field should be required based on conditional logic
 */
export function shouldFieldBeRequired(
  field: FormField,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  // Start with the field's base required status
  let isRequired = field.reqd || false;

  // Find all conditional logic rules that target this field with "Require Answer"
  const targetingRules: ConditionalLogic[] = [];

  allFields.forEach((otherField) => {
    if (!otherField.conditional_logic) return;

    const logic = parseConditionalLogic(otherField.conditional_logic);
    if (
      logic &&
      logic.target_field === field.fieldname &&
      logic.action === Actions.RequireAnswer
    ) {
      targetingRules.push(logic);
    }
  });

  // If any "Require Answer" rule conditions are met, make field required
  for (const rule of targetingRules) {
    if (evaluateConditions(rule, formValues, allFields)) {
      isRequired = true;
      break;
    }
  }

  return isRequired;
}

/**
 * Get all fields that should be visible based on current form values
 */
export function getVisibleFields(
  fields: FormField[],
  formValues: Record<string, any>
): FormField[] {
  return fields.filter((field) =>
    shouldFieldBeVisible(field, formValues, fields)
  );
}

const DISPLAY_ONLY = new Set<string>([
  Fieldtype.HEADING_1,
  Fieldtype.HEADING_2,
  Fieldtype.HEADING_3,
  Fieldtype.PAGE_BREAK,
]);

/** Field types whose answer is picked from the field's own options list. */
const CHOICE_TYPES = new Set<string>([
  Fieldtype.SELECT,
  Fieldtype.SINGLE_CHOICE,
  Fieldtype.MULTISELECT,
]);

export function isChoiceFieldtype(fieldtype: string | undefined): boolean {
  return !!fieldtype && CHOICE_TYPES.has(fieldtype);
}

/** The choices of a Dropdown / Single choice / Multiple choice question. */
export function getChoices(field: Pick<FormField, "options">): string[] {
  return (field.options ?? "")
    .split("\n")
    .map((o) => o.trim())
    .filter(Boolean);
}

/**
 * Questions that appear BEFORE `field` on the form (reading order: row, column,
 * cell), excluding headings and page breaks. Used by the "Show only if..."
 * picker so a question can only depend on an earlier one.
 */
export function getEarlierQuestions(
  field: FormField,
  allFields: FormField[]
): FormField[] {
  const key = (f: FormField) => [
    f.row_index ?? 0,
    f.column_index ?? 0,
    f.cell_index ?? 0,
  ];
  const cmp = (a: FormField, b: FormField) => {
    const ka = key(a);
    const kb = key(b);
    for (let i = 0; i < 3; i++) {
      if (ka[i] !== kb[i]) return ka[i] - kb[i];
    }
    return 0;
  };
  return allFields.filter(
    (f) => f !== field && !DISPLAY_ONLY.has(f.fieldtype) && cmp(f, field) < 0
  );
}
