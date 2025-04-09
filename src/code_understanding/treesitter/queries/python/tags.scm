; Functions
(function_definition
  name: (identifier) @definition.function)

; Classes
(class_definition
  name: (identifier) @definition.class)

; Methods (functions within classes)
(function_definition
  name: (identifier) @definition.method
  [(.parent) @class_parent
  (#match? @class_parent "class_definition")])

; Module-level variables
(assignment
  left: (identifier) @definition.variable
  [(.parent) @module_parent
  (#match? @module_parent "module")])

; Module-level constants (conventionally uppercase)
(assignment
  left: (identifier) @definition.constant
  [(.parent) @module_parent
  (#match? @module_parent "module")]
  (#match? @definition.constant "^[A-Z][A-Z_0-9]*$"))

; Import statements
(import_statement
  name: (dotted_name) @reference.import)

(import_from_statement
  module_name: (dotted_name) @reference.import)