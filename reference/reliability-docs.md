<reliability-docs>
Fit_Everything
classreliability.Fitters.Fit_Everything(failures=None, right_censored=None, exclude=None, sort_by='BIC', method='MLE', optimizer=None, print_results=True, show_histogram_plot=True, show_PP_plot=True, show_probability_plot=True, show_best_distribution_probability_plot=True, downsample_scatterplot=True)
This function will fit all available distributions to the data provided. The only distributions not fitted are Weibull_DSZI and Weibull_ZI. The Beta_2P distribution will only be fitted if the data are between 0 and 1.

Parameters:
failures (array, list) – The failure data. Must have at least 2 elements for all the 2 parameter distributions to be fitted and 3 elements for all distributions to be fitted.

right_censored (array, list, optional) – The right censored data. Optional input. Default = None.

sort_by (str) – Goodness of fit test to sort results by. Must be ‘BIC’,’AICc’,’AD’, or ‘Log-likelihood’. Default is BIC.

show_probability_plot (bool, optional) – Provides a probability plot of each of the fitted distributions. True or False. Default = True

show_histogram_plot (bool, optional) – True or False. Default = True. Will show a histogram (scaled to account for censored data) with the PDF and CDF of each fitted distribution.

show_PP_plot (bool, optional) – Provides a comparison of parametric vs non-parametric fit using Probability-Probability (PP) plot. True or False. Default = True.

show_best_distribution_probability_plot (bool, optional) – Provides a probability plot in a new figure of the best fitting distribution. True or False. Default = True.

exclude (list, array, optional) – List or array of strings specifying which distributions to exclude. Default is None. Options are Weibull_2P, Weibull_3P, Weibull_CR, Weibull_Mixture, Weibull_DS, Normal_2P, Gamma_2P, Loglogistic_2P, Gamma_3P, Lognormal_2P, Lognormal_3P, Loglogistic_3P, Gumbel_2P, Exponential_2P, Exponential_1P, Beta_2P.

print_results (bool, optional) – Will show the results of the fitted parameters and the goodness of fit tests in a dataframe. True/False. Defaults to True.

method (str, optional) – The method used to fit the distribution. Must be either ‘MLE’ (maximum likelihood estimation), ‘LS’ (least squares estimation), ‘RRX’ (Rank regression on X), or ‘RRY’ (Rank regression on Y). LS will perform both RRX and RRY and return the better one. Default is ‘MLE’.

optimizer (str, optional) – The optimization algorithm used to find the solution. Must be either ‘TNC’, ‘L-BFGS-B’, ‘nelder-mead’, or ‘powell’. Specifying the optimizer will result in that optimizer being used. To use all of these specify ‘best’ and the best result will be returned. The default behaviour is to try each optimizer in order (‘TNC’, ‘L-BFGS-B’, ‘nelder-mead’, and ‘powell’) and stop once one of the optimizers finds a solution. If the optimizer fails, the initial guess will be returned. For more detail see the documentation.

downsample_scatterplot (bool, int, optional) – If True or None, and there are over 1000 points, then the scatterplot will be downsampled by a factor. The default downsample factor will seek to produce between 500 and 1000 points. If a number is specified, it will be used as the downsample factor. Default is True. This functionality makes plotting faster when there are very large numbers of points. It only affects the scatterplot not the calculations.

Returns
:
results (dataframe) – a pandas dataframe of results. Fitted parameters in this dataframe may be accessed by name. See below example in Notes.

best_distribution (object) – a reliability.Distributions object created based on the parameters of the best fitting distribution.

best_distribution_name (str) – the name of the best fitting distribution. E.g. ‘Weibull_3P’

parameters and goodness of fit results (float) – This is provided for each fitted distribution. For example, the Weibull_3P distribution values are Weibull_3P_alpha, Weibull_3P_beta, Weibull_3P_gamma, Weibull_3P_BIC, Weibull_3P_AICc, Weibull_3P_AD, Weibull_3P_loglik

excluded_distributions (list) – a list of strings of the excluded distributions.

probability_plot (object) – The figure handle from the probability plot (only provided if show_probability_plot is True).

best_distribution_probability_plot (object) – The figure handle from the best distribution probability plot (only provided if show_best_distribution_probability_plot is True).

histogram_plot (object) – The figure handle from the histogram plot (only provided if show_histogram_plot is True).

PP_plot (object) – The figure handle from the probability-probability plot (only provided if show_PP_plot is True).

Notes

All parametric models have the number of parameters in the name. For example, Weibull_2P uses alpha and beta, whereas Weibull_3P uses alpha, beta, and gamma. This is applied even for Normal_2P for consistency in naming conventions. From the results, the distributions are sorted based on their goodness of fit test results, where the smaller the goodness of fit value, the better the fit of the distribution to the data.

If the data provided contains only 2 failures, the three parameter distributions will automatically be excluded.

Example Usage:

X = [5,3,8,6,7,4,5,4,2]
output = Fit_Everything(X)
print('Weibull Alpha =',output.Weibull_2P_alpha)

Fitting all available distributions to data
'''''''''''''''''''''''''''''''''''''''''''

.. admonition:: API Reference

   For inputs and outputs see the `API reference <https://reliability.readthedocs.io/en/latest/API/Fitters/Fit_Everything.html>`_.

To fit all of the `distributions available <https://reliability.readthedocs.io/en/latest/Fitting%20a%20specific%20distribution%20to%20data.html>`_ in `reliability`, is a similar process to fitting a specific distribution. The user needs to specify the failures and any right censored data. The Beta distribution will only be fitted if you specify data that is in the range 0 to 1 and does not include confidence intervals on the plot. The selection of what can be fitted is all done automatically based on the data provided. Manual exclusion of probability distributions is also possible. If you only provide 2 failures then all distributions with more than 2 parameters will automatically be excluded from the fitting process.

Confidence intervals are shown on the plots but they are not reported for each of the fitted parameters as this would be a large number of outputs. If you need the confidence intervals for the fitted parameters you can repeat the fitting using just a specific distribution and the results will include the confidence intervals. Confidence intervals are not yet available for the Weibull DS, Weibull Mixture, and Weibull CR models.

The distributions Weibull_ZI and Weibull_DSZI are not included when using Fit_Everything as these distributions are only applicable when the dataset contains zeros. If your data contains zeros you should fit these distributions individually.

Example 1
---------

In this first example, we will use `Fit_Everything` on some data and will return only the dataframe of results. Note that we are actively supressing the 4 plots that would normally be shown to provide graphical goodness of fit indications. The table of results has been ranked by BIC to show us that Weibull_2P was the best fitting distribution for this dataset. This is what we expected since the data was generated using Weibull_Distribution(alpha=50,beta=2).

.. code:: python

    from reliability.Fitters import Fit_Everything
    # data created using Weibull_Distribution(alpha=50,beta=2), and rounded to nearest integer
    data = [92, 44, 94, 56, 54, 24, 96, 3, 27, 37, 61, 23, 70, 101, 21, 47, 4, 34, 10, 88, 37, 86, 62, 70, 21, 13, 47, 21, 57, 36, 43, 83, 42, 16, 20, 44, 43, 50, 35, 51, 35, 49, 60, 22, 34, 41, 53, 27, 44, 49]
    Fit_Everything(failures=data, show_histogram_plot=False, show_probability_plot=False, show_PP_plot=False, show_best_distribution_probability_plot=False)

    '''
    Results from Fit_Everything:
    Analysis method: MLE
    Failures / Right censored: 50/0 (0% right censored) 
    
       Distribution   Alpha    Beta  Gamma Alpha 1  Beta 1 Alpha 2  Beta 2 Proportion 1 DS      Mu   Sigma    Lambda  Log-likelihood    AICc     BIC       AD optimizer
         Weibull_2P 51.1908 1.92376                                                                                         -228.338 460.932 464.501 0.613083       TNC
           Gamma_2P 16.5098 2.75836                                                                                         -229.902  464.06 467.628 0.779371       TNC
         Weibull_CR                         52.292 1.78639 98.2941  27.141                                                  -226.049 460.987 467.746 0.654939       TNC
         Weibull_3P 51.1908 1.92376      0                                                                                  -228.338 463.198 468.413 0.613083       TNC
         Weibull_DS 51.1908 1.92376                                                      1                                  -228.338 463.198 468.413 0.613083       TNC
          Normal_2P                                                                          45.54 24.2959                  -230.462  465.18 468.748 0.967238       TNC
    Weibull_Mixture                        44.0526 2.21658 94.6341 17.6943     0.880535                                     -225.092 461.547 469.744  0.61163       TNC
           Gamma_3P 16.5098 2.75836      0                                                                                  -229.902 466.326  471.54 0.779371       TNC
     Loglogistic_2P 40.6775 2.72212                                                                                         -232.426 469.108 472.677 0.754563       TNC
     Loglogistic_3P 40.6775 2.72212      0                                                                                  -232.426 471.374 476.589 0.754563       TNC
       Lognormal_2P                                                                        3.62651  0.7149                  -235.492 475.239 478.808  1.52542       TNC
          Gumbel_2P                                                                        58.2756 25.7469                  -237.148 478.551  482.12  2.19655       TNC
       Lognormal_3P                      0                                                 3.62651  0.7149                  -235.492 477.505  482.72  1.52542       TNC
     Exponential_2P                 2.9999                                                                 0.0235072        -237.522   479.3 482.869  4.27822       TNC
     Exponential_1P                                                                                        0.0219587         -240.93 483.942 485.771  5.05245       TNC
    '''

Example 2
---------

In this second example, we will create some right censored data and use `Fit_Everything`. All outputs are shown, and the best fitting distribution is accessed and printed.

.. code:: python

    from reliability.Fitters import Fit_Everything
    from reliability.Distributions import Weibull_Distribution
    from reliability.Other_functions import make_right_censored_data
    
    raw_data = Weibull_Distribution(alpha=12, beta=3).random_samples(100, seed=2)  # create some data
    data = make_right_censored_data(raw_data, threshold=14)  # right censor the data
    results = Fit_Everything(failures=data.failures, right_censored=data.right_censored)  # fit all the models
    print('The best fitting distribution was', results.best_distribution_name, 'which had parameters', results.best_distribution.parameters)
    
    '''
    Results from Fit_Everything:
    Analysis method: MLE
    Failures / Right censored: 86/14 (14.0% right censored) 
    
       Distribution   Alpha    Beta   Gamma Alpha 1  Beta 1 Alpha 2  Beta 2 Proportion 1       DS      Mu    Sigma    Lambda  Log-likelihood    AICc     BIC      AD optimizer
         Weibull_2P 11.2773 3.30301                                                                                                 -241.959 488.041 493.128  44.945       TNC
          Normal_2P                                                                               10.1194  3.37466                  -242.479 489.082 494.169 44.9098       TNC
           Gamma_2P 1.42301 7.21417                                                                                                 -243.235 490.594  495.68 45.2817       TNC
     Loglogistic_2P 9.86245 4.48433                                                                                                 -243.588 491.301 496.387 45.2002       TNC
         Weibull_DS 10.7383 3.57496                                                      0.930423                                   -241.594 489.437 497.003 44.9447       TNC
         Weibull_3P 10.0786 2.85824 1.15083                                                                                         -241.779 489.807 497.373 44.9927       TNC
    Weibull_Mixture                         3.59763 113.232 11.4208 3.54076    0.0276899                                            -237.392 485.421 497.809 44.9283       TNC
           Gamma_3P 1.42301 7.21417       0                                                                                         -243.235  492.72 500.286 45.2817       TNC
       Lognormal_2P                                                                               2.26524 0.406436                  -245.785 495.694  500.78 45.6874       TNC
     Loglogistic_3P 9.86245 4.48433       0                                                                                         -243.588 493.427 500.992 45.2002       TNC
         Weibull_CR                           12.72 3.30301 15.8031 3.30301                                                         -241.959 492.338 502.338  44.945       TNC
       Lognormal_3P                       0                                                       2.26524 0.406436                  -245.785  497.82 505.385 45.6874       TNC
          Gumbel_2P                                                                               11.5926  2.94944                  -248.348 500.819 505.906 45.4624  L-BFGS-B
     Exponential_2P                 2.82892                                                                         0.121884        -267.003 538.129 543.216 51.7852       TNC
     Exponential_1P                                                                                                0.0870024        -295.996 594.034 596.598 56.8662       TNC 

    
    
    The best fitting distribution was Weibull_2P which had parameters [11.27730641  3.30300712  0.        ]
    '''

.. image:: images/Fit_everything_histogram_plot_V6.png

.. image:: images/Fit_everything_probability_plot_V7.png

.. image:: images/Fit_everything_PP_plot_V6.png

.. image:: images/fit_everything_best_dist.png

All plots are ordered based on the goodness of fit order of the results. For the histogram this is reflected in the order of the legend. For the probability plots and PP plots, these are ordered from top left to bottom right.

Fit_Weibull_Mixture
classreliability.Fitters.Fit_Weibull_Mixture(failures=None, right_censored=None, show_probability_plot=True, print_results=True, CI=0.95, optimizer=None, downsample_scatterplot=True, **kwargs)
Fits a mixture of two Weibull_2P distributions (this does not fit the gamma parameter). Right censoring is supported, though care should be taken to ensure that there still appears to be two groups when plotting only the failure data. A second group cannot be made from a mostly or totally censored set of samples. Use this model when you think there are multiple failure modes acting to create the failure data.

Parameters
:
failures (array, list) – An array or list of the failure data. There must be at least 4 failures, but it is highly recommended to use another model if you have less than 20 failures.

right_censored (array, list, optional) – The right censored data. Optional input. Default = None.

show_probability_plot (bool, optional) – True or False. Default = True

print_results (bool, optional) – Prints a dataframe of the point estimate, standard error, Lower CI and Upper CI for each parameter. True or False. Default = True

optimizer (str, optional) – The optimization algorithm used to find the solution. Must be either ‘TNC’, ‘L-BFGS-B’, ‘nelder-mead’, or ‘powell’. Specifying the optimizer will result in that optimizer being used. To use all of these specify ‘best’ and the best result will be returned. The default behaviour is to try each optimizer in order (‘TNC’, ‘L-BFGS-B’, ‘nelder-mead’, and ‘powell’) and stop once one of the optimizers finds a solution. If the optimizer fails, the initial guess will be returned. For more detail see the documentation.

CI (float, optional) – confidence interval for estimating confidence limits on parameters. Must be between 0 and 1. Default is 0.95 for 95% CI.

downsample_scatterplot (bool, int, optional) – If True or None, and there are over 1000 points, then the scatterplot will be downsampled by a factor. The default downsample factor will seek to produce between 500 and 1000 points. If a number is specified, it will be used as the downsample factor. Default is True. This functionality makes plotting faster when there are very large numbers of points. It only affects the scatterplot not the calculations.

kwargs – Plotting keywords that are passed directly to matplotlib for the probability plot (e.g. color, label, linestyle)

Returns
:
alpha_1 (float) – the fitted Weibull_2P alpha parameter for the first (left) group

beta_1 (float) – the fitted Weibull_2P beta parameter for the first (left) group

alpha_2 (float) – the fitted Weibull_2P alpha parameter for the second (right) group

beta_2 (float) – the fitted Weibull_2P beta parameter for the second (right) group

proportion_1 (float) – the fitted proportion of the first (left) group

proportion_2 (float) – the fitted proportion of the second (right) group. Same as 1-proportion_1

alpha_1_SE (float) – the standard error (sqrt(variance)) of the parameter

beta_1_SE (float) – the standard error (sqrt(variance)) of the parameter

alpha_2_SE (float) – the standard error (sqrt(variance)) of the parameter

beta_2_SE (float) – the standard error (sqrt(variance)) of the parameter

proportion_1_SE (float) – the standard error (sqrt(variance)) of the parameter

alpha_1_upper (float) – the upper CI estimate of the parameter

alpha_1_lower (float) – the lower CI estimate of the parameter

alpha_2_upper (float) – the upper CI estimate of the parameter

alpha_2_lower (float) – the lower CI estimate of the parameter

beta_1_upper (float) – the upper CI estimate of the parameter

beta_1_lower (float) – the lower CI estimate of the parameter

beta_2_upper (float) – the upper CI estimate of the parameter

beta_2_lower (float) – the lower CI estimate of the parameter

proportion_1_upper (float) – the upper CI estimate of the parameter

proportion_1_lower (float) – the lower CI estimate of the parameter

loglik (float) – Log Likelihood (as used in Minitab and Reliasoft)

loglik2 (float) – LogLikelihood*-2 (as used in JMP Pro)

AICc (float) – Akaike Information Criterion

BIC (float) – Bayesian Information Criterion

AD (float) – the Anderson Darling (corrected) statistic (as reported by Minitab)

distribution (object) – a Mixture_Model object with the parameters of the fitted distribution

results (dataframe) – a pandas dataframe of the results (point estimate, standard error, lower CI and upper CI for each parameter)

goodness_of_fit (dataframe) – a pandas dataframe of the goodness of fit values (Log-likelihood, AICc, BIC, AD).

probability_plot (object) – the axes handle for the probability plot. This is only returned if show_probability_plot = True

Notes

This is different to the Weibull Competing Risks as the overall Survival Function is the sum of the individual Survival Functions multiplied by a proportion rather than being the product as is the case in the Weibull Competing Risks Model.

Mixture Model: 

Competing Risks Model: 

Similar to the competing risks model, you can use this model when you think there are multiple failure modes acting to create the failure data.

Whilst some failure modes may not be fitted as well by a Weibull distribution as they may be by another distribution, it is unlikely that a mixture of data from two distributions (particularly if they are overlapping) will be fitted noticeably better by other types of mixtures than would be achieved by a Weibull mixture. For this reason, other types of mixtures are not implemented.

If the fitting process encounters a problem a warning will be printed. This may be caused by the chosen distribution being a very poor fit to the data or the data being heavily censored. If a warning is printed, consider trying a different optimizer.

staticLL(params, T_f, T_rc)
staticlogR(t, a1, b1, a2, b2, p)
staticlogf(t, a1, b1, a2, b2, p)


Mixture models
''''''''''''''

What are mixture models?
========================

Mixture models are a combination of two or more distributions added together to create a distribution that has a shape with more flexibility than a single distribution. Each of the mixture's components must be multiplied by a proportion, and the sum of all the proportions is equal to 1. The mixture is generally written in terms of the PDF, but since the CDF is the integral (cumulative sum) of the PDF, we can equivalently write the Mixture model in terms of the PDF or CDF. For a mixture model with 2 distributions, the equations are shown below:

:math:`{PDF}_{mixture} = p\times{PDF}_1 + (1-p)\times{PDF}_2`

:math:`{CDF}_{mixture} = p\times{CDF}_1 + (1-p)\times{CDF}_2`

:math:`{SF}_{mixture} = 1-{CDF}_{mixture}`

:math:`{HF}_{mixture} = \frac{{PDF}_{mixture}}{{SF}_{mixture}}`

:math:`{CHF}_{mixture} = -ln({SF}_{mixture})`

Mixture models are useful when there is more than one failure mode that is generating the failure data. This can be recognised by the shape of the PDF and CDF being outside of what any single distribution can accurately model. On a probability plot, a mixture of failure modes can be identified by bends or S-shapes in the data that you might otherwise expect to be linear. An example of this is shown in the image below. You should not use a mixture model just because it can fit almost anything really well, but you should use a mixture model if you suspect that there are multiple failure modes contributing to the failure data you are observing. To judge whether a mixture model is justified, look at the goodness of fit criterion (AICc or BIC) which penalises the score based on the number of parameters in the model. The closer the goodness of fit criterion is to zero, the better the fit. Using AD or log-likelihood for this check is not appropriate as these goodness of fit criterions do not penalise the score based on the number of parameters in the model and are therefore prone to overfitting.

See also `competing risk models <https://reliability.readthedocs.io/en/latest/Competing%20risk%20models.html>`_ for another method of combining distributions using the product of the SF rather than the sum of the CDF.

.. image:: images/mixture_required1.png

Creating a mixture model
========================

Within `reliability.Distributions` is the Mixture_Model. This function accepts an array or list of standard distribution objects created using the `reliability.Distributions` module (available distributions are Exponential, Weibull, Gumbel, Normal, Lognormal, Loglogistic, Gamma, Beta). There is no limit to the number of components you can add to the mixture, but it is generally preferable to use as few as are required to fit the data appropriately (typically 2 or 3). In addition to the distributions, you can specify the proportions contributed by each distribution in the mixture. These proportions must sum to 1. If not specified the proportions will be set as equal for each component.

As this process is additive for the survival function, and may accept many distributions of different types, the mathematical formulation quickly gets complex. For this reason, the algorithm combines the models numerically rather than empirically so there are no simple formulas for many of the descriptive statistics (mean, median, etc.). Also, the accuracy of the model is dependent on xvals. If the xvals array is small (<100 values) then the answer will be "blocky" and inaccurate. The variable xvals is only accepted for PDF, CDF, SF, HF, and CHF. The other methods (like random samples) use the default xvals for maximum accuracy. The default number of values generated when xvals is not given is 1000. Consider this carefully when specifying xvals in order to avoid inaccuracies in the results.

.. admonition:: API Reference

   For inputs and outputs see the `API reference <https://reliability.readthedocs.io/en/latest/API/Distributions/Mixture_Model.html>`_.

Example 1
---------

The following example shows how the Mixture_Model object can be created, visualised and used.

.. code:: python

    from reliability.Distributions import Lognormal_Distribution, Gamma_Distribution, Weibull_Distribution, Mixture_Model
    import matplotlib.pyplot as plt

    # create the mixture model
    d1 = Lognormal_Distribution(mu=2, sigma=0.8)
    d2 = Weibull_Distribution(alpha=50, beta=5, gamma=100)
    d3 = Gamma_Distribution(alpha=5, beta=3, gamma=30)
    mixture_model = Mixture_Model(distributions=[d1, d2, d3], proportions=[0.3, 0.4, 0.3])

    # plot the 5 functions using the plot() function
    mixture_model.plot()

    # plot the PDF and CDF
    plot_components = True # this plots the component distributions. Default is False
    plt.figure(figsize=(9, 5))
    plt.subplot(121)
    mixture_model.PDF(plot_components=plot_components, color='red', linestyle='--')
    plt.subplot(122)
    mixture_model.CDF(plot_components=plot_components, color='red', linestyle='--')
    plt.subplots_adjust(left=0.1, right=0.95)
    plt.show()

    # extract the mean of the distribution
    print('The mean of the distribution is:', mixture_model.mean)
    
    '''
    The mean of the distribution is: 74.91607709895453
    '''

.. image:: images/Weibull_Mixture_distV1.png

.. image:: images/Weibull_Mixture_dist_propsV1.png

Fitting a mixture model
=======================

Within `reliability.Fitters` is Fit_Weibull_Mixture. This function will fit a Weibull Mixture Model consisting of 2 x Weibull_2P distributions (this does not fit the gamma parameter). Just as with all of the other distributions in `reliability.Fitters`, right censoring is supported, though care should be taken to ensure that there still appears to be two groups when plotting only the failure data. A second group cannot be made from a mostly or totally censored set of samples.

Whilst some failure modes may not be fitted as well by a Weibull distribution as they may be by another distribution, it is unlikely that a mixture of data from two distributions (particularly if they are overlapping) will be fitted noticeably better by other types of mixtures than would be achieved by a Weibull mixture. For this reason, other types of mixtures are not implemented.

.. admonition:: API Reference

   For inputs and outputs see the `API reference <https://reliability.readthedocs.io/en/latest/API/Fitters/Fit_Weibull_Mixture.html>`_.

Example 2
---------

In this example, we will create some data using two Weibull distributions and then combine the data using np.hstack. We will then fit the Weibull mixture model to the combined data and will print the results and show the plot. As the input data is made up of 40% from the first group, we expect the proportion to be around 0.4.

.. code:: python

    from reliability.Fitters import Fit_Weibull_Mixture
    from reliability.Distributions import Weibull_Distribution
    from reliability.Other_functions import histogram
    import numpy as np
    import matplotlib.pyplot as plt
    
    # create some failures from two distributions
    group_1 = Weibull_Distribution(alpha=10, beta=3).random_samples(40, seed=2)
    group_2 = Weibull_Distribution(alpha=40, beta=4).random_samples(60, seed=2)
    all_data = np.hstack([group_1, group_2])  # combine the data
    results = Fit_Weibull_Mixture(failures=all_data) #fit the mixture model

    # this section is to visualise the histogram with PDF and CDF
    # it is not part of the default output from the Fitter
    plt.figure(figsize=(9, 5))
    plt.subplot(121)
    histogram(all_data)
    results.distribution.PDF()
    plt.subplot(122)
    histogram(all_data, cumulative=True)
    results.distribution.CDF()

    plt.show()

    '''
    Results from Fit_Weibull_Mixture (95% CI):
    Analysis method: Maximum Likelihood Estimation (MLE)
    Optimizer: TNC
    Failures / Right censored: 100/0 (0% right censored) 
    
       Parameter  Point Estimate  Standard Error  Lower CI  Upper CI
         Alpha 1         8.65511        0.393835   7.91663   9.46248
          Beta 1         3.91197        0.509776   3.03021    5.0503
         Alpha 2         38.1103         1.41075   35.4431   40.9781
          Beta 2         3.82192        0.421385   3.07916   4.74385
    Proportion 1        0.388491       0.0502663  0.295595  0.490263 
    
    Goodness of fit    Value
     Log-likelihood -375.991
               AICc  762.619
                BIC  775.007
                 AD 0.418649 
    '''

.. image:: images/Weibull_Mixture_V6.png

.. image:: images/Weibull_Mixture_histV2.png

Example 3
---------

In this example, we will compare how well the Weibull Mixture performs vs a single Weibull_2P. Firstly, we generate some data from two Weibull distributions, combine the data, and right censor it above our chosen threshold. Next, we will fit the Mixture and Weibull_2P distributions. Then we will visualise the histogram and PDF of the fitted mixture model and Weibull_2P distributions. The goodness of fit measure is used to check whether the mixture model is really a much better fit than a single Weibull_2P distribution (which it is due to the lower BIC).

.. code:: python
  
    from reliability.Fitters import Fit_Weibull_Mixture, Fit_Weibull_2P
    from reliability.Distributions import Weibull_Distribution
    from reliability.Other_functions import histogram, make_right_censored_data
    import numpy as np
    import matplotlib.pyplot as plt

    # create some failures and right censored data
    group_1 = Weibull_Distribution(alpha=10, beta=2).random_samples(700, seed=2)
    group_2 = Weibull_Distribution(alpha=30, beta=3).random_samples(300, seed=2)
    all_data = np.hstack([group_1, group_2])
    data = make_right_censored_data(all_data, threshold=30)

    # fit the Weibull Mixture and Weibull_2P
    mixture = Fit_Weibull_Mixture(failures=data.failures, right_censored=data.right_censored, show_probability_plot=False, print_results=False)
    single = Fit_Weibull_2P(failures=data.failures, right_censored=data.right_censored, show_probability_plot=False, print_results=False)
    print('Weibull_Mixture BIC:', mixture.BIC, '\nWeibull_2P BIC:', single.BIC) # print the goodness of fit measure

    # plot the Mixture and Weibull_2P
    histogram(all_data, white_above=30)
    mixture.distribution.PDF(label='Weibull Mixture')
    single.distribution.PDF(label='Weibull_2P')
    plt.title('Comparison of Weibull_2P with Weibull Mixture')
    plt.legend()
    plt.show()

    '''
    Weibull_Mixture BIC: 6431.578404076784
    Weibull_2P BIC: 6511.511759597337
    '''

.. image:: images/Weibull_mixture_vs_Weibull_2P_V5.png


Fit_Weibull_CR
classreliability.Fitters.Fit_Weibull_CR(failures=None, right_censored=None, show_probability_plot=True, print_results=True, CI=0.95, optimizer=None, downsample_scatterplot=True, **kwargs)
Fits a Weibull Competing Risks Model consisting of two Weibull_2P distributions (this does not fit the gamma parameter). Similar to the mixture model, you can use this model when you think there are multiple failure modes acting to create the failure data.

Parameters
:
failures (array, list) – An array or list of the failure data. There must be at least 4 failures, but it is highly recommended to use another model if you have less than 20 failures.

right_censored (array, list, optional) – The right censored data. Optional input. Default = None.

show_probability_plot (bool, optional) – True or False. Default = True

print_results (bool, optional) – Prints a dataframe of the point estimate, standard error, Lower CI and Upper CI for each parameter. True or False. Default = True

optimizer (str, optional) – The optimization algorithm used to find the solution. Must be either ‘TNC’, ‘L-BFGS-B’, ‘nelder-mead’, or ‘powell’. Specifying the optimizer will result in that optimizer being used. To use all of these specify ‘best’ and the best result will be returned. The default behaviour is to try each optimizer in order (‘TNC’, ‘L-BFGS-B’, ‘nelder-mead’, and ‘powell’) and stop once one of the optimizers finds a solution. If the optimizer fails, the initial guess will be returned. For more detail see the documentation.

CI (float, optional) – confidence interval for estimating confidence limits on parameters. Must be between 0 and 1. Default is 0.95 for 95% CI.

downsample_scatterplot (bool, int, optional) – If True or None, and there are over 1000 points, then the scatterplot will be downsampled by a factor. The default downsample factor will seek to produce between 500 and 1000 points. If a number is specified, it will be used as the downsample factor. Default is True. This functionality makes plotting faster when there are very large numbers of points. It only affects the scatterplot not the calculations.

kwargs – Plotting keywords that are passed directly to matplotlib for the probability plot (e.g. color, label, linestyle)

Returns
:
alpha_1 (float) – the fitted Weibull_2P alpha parameter for the first distribution

beta_1 (float) – the fitted Weibull_2P beta parameter for the first distribution

alpha_2 (float) – the fitted Weibull_2P alpha parameter for the second distribution

beta_2 (float) – the fitted Weibull_2P beta parameter for the second distribution

alpha_1_SE (float) – the standard error (sqrt(variance)) of the parameter

beta_1_SE (float) – the standard error (sqrt(variance)) of the parameter

alpha_2_SE (float) – the standard error (sqrt(variance)) of the parameter

beta_2_SE (float) – the standard error (sqrt(variance)) of the parameter

alpha_1_upper (float) – the upper CI estimate of the parameter

alpha_1_lower (float) – the lower CI estimate of the parameter

alpha_2_upper (float) – the upper CI estimate of the parameter

alpha_2_lower (float) – the lower CI estimate of the parameter

beta_1_upper (float) – the upper CI estimate of the parameter

beta_1_lower (float) – the lower CI estimate of the parameter

beta_2_upper (float) – the upper CI estimate of the parameter

beta_2_lower (float) – the lower CI estimate of the parameter

loglik (float) – Log Likelihood (as used in Minitab and Reliasoft)

loglik2 (float) – LogLikelihood*-2 (as used in JMP Pro)

AICc (float) – Akaike Information Criterion

BIC (float) – Bayesian Information Criterion

AD (float) – the Anderson Darling (corrected) statistic (as reported by Minitab)

distribution (object) – a Competing_Risks_Model object with the parameters of the fitted distribution

results (dataframe) – a pandas dataframe of the results (point estimate, standard error, lower CI and upper CI for each parameter)

goodness_of_fit (dataframe) – a pandas dataframe of the goodness of fit values (Log-likelihood, AICc, BIC, AD).

probability_plot (object) – the axes handle for the probability plot. This is only returned if show_probability_plot = True

Notes

This is different to the Weibull Mixture model as the overall Survival Function is the product of the individual Survival Functions rather than being the sum as is the case in the Weibull Mixture Model.

Mixture Model: 

Competing Risks Model: 

Whilst some failure modes may not be fitted as well by a Weibull distribution as they may be by another distribution, it is unlikely that data from a competing risks model will be fitted noticeably better by other types of competing risks models than would be achieved by a Weibull Competing Risks model. For this reason, other types of competing risks models are not implemented.

staticLL(params, T_f, T_rc)
staticlogR(t, a1, b1, a2, b2)
staticlogf(t, a1, b1, a2, b2)

Competing risks models
''''''''''''''''''''''

What are competing risks models?
================================

Competing risks models are a combination of two or more distributions that represent failure modes which are "competing" to end the life of the system being modelled. This model is similar to a `mixture model <https://reliability.readthedocs.io/en/latest/Mixture%20models.html>`_ in the sense that it uses multiple distributions to create a new model that has a shape with more flexibility than a single distribution. However, unlike in mixture models, we are not adding proportions of the PDF or CDF, but are instead multiplying the survival functions. The formula for the competing risks model is typically written in terms of the survival function (SF). Since we may consider the system's reliability to depend on the reliability of all the parts of the system (each with its own failure modes), the equation is written as if the system was in series, using the product of the survival functions for each failure mode. For a competing risks model with 2 distributions, the equations are shown below:

:math:`{SF}_{Competing\,Risks} = {SF}_1 \times {SF}_2`

:math:`{CDF}_{Competing\,Risks} = 1-{SF}_{Competing\,Risks}`

Since :math:`{SF} = exp(-CHF)` we may equivalently write the competing risks model in terms of the hazard or cumulative hazard function as:

:math:`{HF}_{Competing\,Risks} = {HF}_1 + {HF}_2`

:math:`{CHF}_{Competing\,Risks} = {CHF}_1 + {CHF}_2`

:math:`{PDF}_{Competing\,Risks} = {HF}_{Competing\,Risks} \times {SF}_{Competing\,Risks}`

The image below illustrates the difference between the competing risks model and the mixture model, each of which is made up of the same two component distributions. Note that the PDF of the competing risks model is always equal to or to the left of the component distributions, and the CDF is equal to or higher than the component distributions. This shows how a failure mode that occurs earlier in time can end the lives of units under observation before the second failure mode has the chance to. This behaviour is characteristic of real systems which experience multiple failure modes, each of which could cause system failure.

.. image:: images/CRvsMM1.png

Competing risks models are useful when there is more than one failure mode that is generating the failure data. This can be recognised by the shape of the PDF and CDF being outside of what any single distribution can accurately model. On a probability plot, a combination of failure modes can be identified by bends in the data that you might otherwise expect to be linear. An example of this is shown in the image below. You should not use a competing risks model just because it fits your data better than a single distribution, but you should use a competing risks model if you suspect that there are multiple failure modes contributing to the failure data you are observing. To judge whether a competing risks model is justified, look at the goodness of fit criterion (AICc or BIC) which penalises the score based on the number of parameters in the model. The closer the goodness of fit criterion is to zero, the better the fit. It is not appropriate to use the Log-likelihood or AD goodness of fit criterions as these do not penalise the score based on the number of parameters, therefore making the model susceptible to overfitting.

See also `mixture models <https://reliability.readthedocs.io/en/latest/Mixture%20models.html>`_ for another method of combining distributions using the sum of the CDF rather than the product of the SF.

.. image:: images/CRprobplot1.png

Creating a competing risks model
================================

Within `reliability.Distributions` is the Competing_Risks_Model. This function accepts an array or list of distribution objects created using the reliability.Distributions module (available distributions are Exponential, Weibull, Gumbel, Normal, Lognormal, Loglogistic, Gamma, Beta). There is no limit to the number of components you can add to the model, but it is generally preferable to use as few as are required to fit the data appropriately (typically 2 or 3). Unlike the mixture model, you do not need to specify any proportions.

As this process is multiplicative for the survival function (or additive for the hazard function), and may accept many distributions of different types, the mathematical formulation quickly gets complex. For this reason, the algorithm combines the models numerically rather than empirically so there are no simple formulas for many of the descriptive statistics (mean, median, etc.). Also, the accuracy of the model is dependent on xvals. If the xvals array is small (<100 values) then the answer will be вЂњblockyвЂќ and inaccurate. The variable xvals is only accepted for PDF, CDF, SF, HF, and CHF. The other methods (like random samples) use the default xvals for maximum accuracy. The default number of values generated when xvals is not given is 1000. Consider this carefully when specifying xvals in order to avoid inaccuracies in the results.

.. admonition:: API Reference

   For inputs and outputs see the `API reference <https://reliability.readthedocs.io/en/latest/API/Distributions/Competing_Risks_Model.html>`_.

Example 1
---------

The following example shows how the Competing_Risks_Model object can be created, visualised and used.

.. code:: python

    from reliability.Distributions import Lognormal_Distribution, Gamma_Distribution, Weibull_Distribution, Competing_Risks_Model
    import matplotlib.pyplot as plt

    # create the competing risks model
    d1 = Lognormal_Distribution(mu=4, sigma=0.1)
    d2 = Weibull_Distribution(alpha=50, beta=2)
    d3 = Gamma_Distribution(alpha=30,beta=1.5)
    CR_model = Competing_Risks_Model(distributions=[d1, d2, d3])

    # plot the 5 functions using the plot() function
    CR_model.plot()

    # plot the PDF and CDF
    plot_components = True # this plots the component distributions. Default is False
    plt.figure(figsize=(9, 5))
    plt.subplot(121)
    CR_model.PDF(plot_components=plot_components, color='red', linestyle='--')
    plt.subplot(122)
    CR_model.CDF(plot_components=plot_components, color='red', linestyle='--')
    plt.show()

    # extract the mean of the distribution
    print('The mean of the distribution is:', CR_model.mean)

    '''
    The mean of the distribution is: 27.04449126273065
    '''

.. image:: images/CR_model_plotV2.png

.. image:: images/CR_model_PDF_CDFV2.png

Fitting a competing risks model
===============================

Within `reliability.Fitters` is Fit_Weibull_CR. This function will fit a Weibull Competing Risks Model consisting of 2 x Weibull_2P distributions (this does not fit the gamma parameter). Just as with all of the other distributions in `reliability.Fitters`, right censoring is supported.

Whilst some failure modes may not be fitted as well by a Weibull distribution as they may be by another distribution, it is unlikely that a competing risks model of data from two distributions (particularly if they are overlapping) will be fitted noticeably better by other types of competing risks models than would be achieved by a Weibull Competing Risks Model. For this reason, other types of competing risks models are not implemented.

.. admonition:: API Reference

   For inputs and outputs see the `API reference <https://reliability.readthedocs.io/en/latest/API/Fitters/Fit_Weibull_CR.html>`_.

Example 2
---------

In this example, we will create some data using a competing risks model from two Weibull distributions. We will then fit the Weibull mixture model to the data and will print the results and show the plot.

.. code:: python

    from reliability.Distributions import Weibull_Distribution, Competing_Risks_Model
    from reliability.Fitters import Fit_Weibull_CR
    from reliability.Other_functions import histogram
    import matplotlib.pyplot as plt

    # create some data that requires a competing risks models
    d1 = Weibull_Distribution(alpha=50, beta=2)
    d2 = Weibull_Distribution(alpha=40, beta=10)
    CR_model = Competing_Risks_Model(distributions=[d1, d2])
    data = CR_model.random_samples(100, seed=2)

    # fit the Weibull competing risks model
    results = Fit_Weibull_CR(failures=data)

    # this section is to visualise the histogram with PDF and CDF
    # it is not part of the default output from the Fitter
    plt.figure(figsize=(9, 5))
    plt.subplot(121)
    histogram(data)
    results.distribution.PDF()
    plt.subplot(122)
    histogram(data, cumulative=True)
    results.distribution.CDF()

    plt.show()

    '''
    Results from Fit_Weibull_CR (95% CI):
    Analysis method: Maximum Likelihood Estimation (MLE)
    Optimizer: L-BFGS-B
    Failures / Right censored: 100/0 (0% right censored) 
    
    Parameter  Point Estimate  Standard Error  Lower CI  Upper CI
      Alpha 1         55.2695         14.3883   33.1812   92.0615
       Beta 1         1.89484        0.452994   1.18598   3.02738
      Alpha 2          38.175         1.07992    36.116   40.3514
       Beta 2         7.97514         1.18035   5.96701   10.6591 
    
    Goodness of fit    Value
     Log-likelihood -352.479
               AICc   713.38
                BIC  723.379
                 AD 0.390325
    '''

.. image:: images/CR_fit_probplot2.png

.. image:: images/CR_fit_hist1.png

Example 3
---------

In this example, we will compare the mixture model to the competing risks model. The data is generated from a competing risks model so we expect the Weibull competing risks model to be more appropriate than the Mixture model. Through comparison of the AICc or BIC, we can see which model is more appropriate. Since the AICc and BIC penalise the goodness of fit criterion based on the number of parameters and the mixture model has 5 parameters compared to the competing risk model's 4 parameters, we expect the competing risks model to have a lower (closer to zero) goodness of fit than the Mixture model, and this is what we observe in the results. Notice how the log-likelihood and AD statistics of the mixture model indicates a better fit (because the value is closer to zero), but this does not take into account the number of parameters in the model.

.. code:: python

    from reliability.Distributions import Weibull_Distribution, Competing_Risks_Model
    from reliability.Fitters import Fit_Weibull_CR, Fit_Weibull_Mixture
    import matplotlib.pyplot as plt
    import pandas as pd

    # create some data from a competing risks model
    d1 = Weibull_Distribution(alpha=250, beta=2)
    d2 = Weibull_Distribution(alpha=210, beta=10)
    CR_model = Competing_Risks_Model(distributions=[d1, d2])
    data = CR_model.random_samples(50, seed=2)

    CR_fit = Fit_Weibull_CR(failures=data)  # fit the Weibull competing risks model
    print('----------------------------------------')
    MM_fit = Fit_Weibull_Mixture(failures=data)  # fit the Weibull mixture model
    plt.legend()
    plt.show()
    print('----------------------------------------')
    
    # create a dataframe to display the goodness of fit criterion as a table
    goodness_of_fit = {'Model': ['Competing Risks', 'Mixture'], 'AICc': [CR_fit.AICc, MM_fit.AICc], 'BIC': [CR_fit.BIC, MM_fit.BIC], 'AD': [CR_fit.AD, MM_fit.AD]}
    df = pd.DataFrame(goodness_of_fit, columns=['Model', 'AICc', 'BIC', 'AD'])
    print(df)

    '''
    Results from Fit_Weibull_CR (95% CI):
    Analysis method: Maximum Likelihood Estimation (MLE)
    Optimizer: L-BFGS-B
    Failures / Right censored: 50/0 (0% right censored) 
    
    Parameter  Point Estimate  Standard Error  Lower CI  Upper CI
      Alpha 1         229.868         51.2178   148.531   355.744
       Beta 1         2.50124        0.747103   1.39286   4.49162
      Alpha 2         199.717         8.56554   183.615   217.231
       Beta 2         9.20155         2.20135   5.75734   14.7062 
    
    Goodness of fit    Value
     Log-likelihood -255.444
               AICc  519.777
                BIC  526.536
                 AD 0.582534 
    
    ----------------------------------------
    Results from Fit_Weibull_Mixture (95% CI):
    Analysis method: Maximum Likelihood Estimation (MLE)
    Optimizer: TNC
    Failures / Right censored: 50/0 (0% right censored) 
    
       Parameter  Point Estimate  Standard Error  Lower CI  Upper CI
         Alpha 1          100.43         12.4535    78.761    128.06
          Beta 1         4.07764          1.2123   2.27689   7.30257
         Alpha 2         189.763         5.13937   179.953   200.108
          Beta 2         7.70223         1.35191   5.46024   10.8648
    Proportion 1        0.215599       0.0815976 0.0964618  0.414394 
    
    Goodness of fit    Value
     Log-likelihood -254.471
               AICc  520.306
                BIC  528.503
                 AD 0.529294 
    
    ----------------------------------------
                 Model    AICc     BIC       AD
    0  Competing Risks 519.777 526.536 0.582534
    1          Mixture 520.306 528.503 0.529294
    '''

.. image:: images/CRvsMM_fitV4.png
</reliability-docs>