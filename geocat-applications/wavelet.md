
## Wavelet
 Computes the wavelet of time-series data

## How to Run Wavelets in NCL
[NCL Wavelet function](https://www.ncl.ucar.edu/Document/Functions/Built-in/wavelet.shtml)

```
function wavelet (
	y        [*] : numeric,  
	mother   [1] : integer,  
	dt       [1] : numeric,  
	param    [1] : numeric,  
	s0       [1] : numeric,  
	dj       [1] : numeric,  
	jtot     [1] : integer,  
	npad     [1] : integer,  
	noise    [1] : integer,  
	isigtest [1] : integer,  
	siglvl   [1] : numeric,  
	nadof    [*] : numeric   
)


Return value [2][jtot][dimsizes(y)] :  float or double
```
### Input Values
y: input data as a one-dimesional array (length N)

mother: integer to specify mother wavelet, defaults to 0 (0 = "Morlet", 1 = "Paul", 2 = "DOG")

dt: sampling time (time between y-values)

param: mother wavelet parameter (Morlet wavenumber = 6, Paul m order = 4, DOG m-th derivative = 2)

s0: smallest scale

dj: space between scales

jtot: largest scale

npad: pad with extra zeroes to prevent wavelet cutoff that can impact coi

noise: test vs. red noise for significance testing

isigtest: 0 = chi-square test, 1=time-average test

siglvl: significance level

nadof: ignored by NCL

### Return Value
Returns an array of wavelet coefficients where: Real (0, 0, 0), Imaginary (1, 0, 0) 


## How to Compute Wavelets in Python
[PyWavelets](https://pywavelets.readthedocs.io/en/latest/ref/cwt.html) compute wavelet coefficients

```
pywt.cwt(data, scales, wavelet, sampling_period)
```

### Input Values

data: inpt data as a array_like

scales: array_like collection of the scales to use (np.arange(s0, jtot, dj))

wavelet: wavelet to use

sampling_period: optional sampling period for frequencies output

### Return Value

coefs: array_like complex number output for wavelet coefficients

frequencies: array_like frequencies
