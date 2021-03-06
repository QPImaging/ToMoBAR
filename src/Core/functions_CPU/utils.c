/*
This work is part of the Core Imaging Library developed by
Visual Analytics and Imaging System Group of the Science Technology
Facilities Council, STFC

Copyright 2017 Daniil Kazanteev

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

#include "utils.h"
#include <math.h>

/* Copy Image (float) */
float copyIm(float *A, float *U, long dimX, long dimY, long dimZ)
{
	long j;
#pragma omp parallel for shared(A, U) private(j)
	for (j = 0; j<dimX*dimY*dimZ; j++)  U[j] = A[j];
	return *U;
}

/* Copy Image */
unsigned char copyIm_unchar(unsigned char *A, unsigned char *U, int dimX, int dimY, int dimZ)
{
	int j;
#pragma omp parallel for shared(A, U) private(j)
	for (j = 0; j<dimX*dimY*dimZ; j++)  U[j] = A[j];
	return *U;
}
