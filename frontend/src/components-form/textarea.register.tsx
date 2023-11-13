import { FieldValues, RegisterOptions, UseFormRegister, UseFormSetValue } from "react-hook-form";
import { FormFieldError } from "../screens/edit-form-hook/form";
import { OpsTextarea } from "./textarea";

interface Props {
  name: string;
  label: string;
  value: string;
  register: UseFormRegister<FieldValues>;
  config?: RegisterOptions<FieldValues, string> | undefined;
  setValue: UseFormSetValue<FieldValues>;
  error?: FormFieldError;
  isProtected?: boolean;
  isOptionnal?: boolean;
  disabled?: boolean;
}

export const OpsTextareaRegister = (props: Props) => {
  const { name, register, setValue, config, ...propsToPass } = props;

  const inputRegister = register(name, {
    value: props.value ?? "",
    ...config,
  });

  return <OpsTextarea {...propsToPass} onChange={(value) => setValue(inputRegister.name, value)} />;
};
