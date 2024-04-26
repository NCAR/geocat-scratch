## sin
 Computes the sine of numeric types.

## How to Compute Sin in NCL
[NCL sin function](https://www.ncl.ucar.edu/Document/Functions/Built-in/sin.shtml)

```
function sin (
	value  : numeric   
)

Return value [dimsizes(value)] as float or double
```
### Input Values
Input value of  one or more values of any dimension, in radians

### Return Value
Returns an array dimensioned the same as the input value. The return type is double if the input is double, and float otherwise

### NCL Example:
```
sin_f = sin(0.5)
print(sin_f)
```
Returned value is 0.4794255

## How to Compute Sin in Python
[Numpy sin](https://numpy.org/doc/stable/reference/generated/numpy.sin.html) computes trigonometric sine, element-wise.

```
numpy.sin(x)
```
Return array like value as float

### Input Values
Input value of angles in radians

### Return Value
Returns an array of sine of each element of input x. This is a scalar if x is a scalar.

### Python Example:
```python
import numpy as np
sin_f = np.sin(f)
print(sin_f)

```
Returned value is 0.479425538604203
