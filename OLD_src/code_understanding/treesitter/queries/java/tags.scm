; Class definitions
((class_declaration
  name: (identifier) @name
  body: (class_body) @scope)
  @class)

; Method definitions
((method_declaration
  name: (identifier) @name
  body: (block) @scope)
  @function)