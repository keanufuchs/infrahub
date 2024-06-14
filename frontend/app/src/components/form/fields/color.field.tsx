import { FormField, FormInput, FormMessage } from "@/components/ui/form";
import { FormFieldProps } from "@/components/form/type";
import { InputProps } from "@/components/ui/input";
import { ColorPicker } from "@/components/inputs/color-picker";
import { LabelFormField } from "@/components/form/fields/common";

export interface InputFieldProps
  extends FormFieldProps,
    Omit<InputProps, "defaultValue" | "name"> {}

const ColorField = ({
  defaultValue,
  description,
  label,
  name,
  rules,
  unique,
  ...props
}: InputFieldProps) => {
  return (
    <FormField
      key={name}
      name={name}
      rules={rules}
      defaultValue={defaultValue}
      render={({ field }) => {
        // Not passing value is needed to prevent error on uncontrolled component
        // eslint-disable-next-line @typescript-eslint/no-unused-vars,no-unused-vars
        const { value, ...fieldMethodsWithoutValue } = field;
        return (
          <div className="relative flex flex-col">
            <LabelFormField
              label={label}
              unique={unique}
              required={!!rules?.required}
              description={description}
            />

            <FormInput>
              <ColorPicker {...field} className {...props} />
            </FormInput>
            <FormMessage />
          </div>
        );
      }}
    />
  );
};

export default ColorField;
