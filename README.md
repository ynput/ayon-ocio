# AYON OCIO configs
Support OCIO default AYON configs to ayon-launcher. The addon is quite simple, all what is needed is client code with configs.

### How it works
Create package script downloads configs from predefined url and copy the content to client code.


### Output client structure
```
└─ ayon_ocio
  ├─ __init__.py
  ├─ version.py
  └─ configs
    └─ OpenColorIOConfigs
      └─ ...
```
