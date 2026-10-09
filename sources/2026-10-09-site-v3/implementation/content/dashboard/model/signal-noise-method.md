# Experimental signal/noise alternative

This is our local implementation inspired by Ariel Danieli and
[To120](https://twonetwenty.com/he/methodology). It is not their source code,
calibration, exact model, or published forecast. The local-level Kalman filtering
and predictive likelihood approach follows standard
[state-space methodology](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_concentrated_scale.html).

For each party separately, vote shares are fractions, not percentages:

```
x(t) = x(t-1) + eta(t), eta(t) ~ N(0, Q * elapsed_days)
y(t) = x(t) + b(institute) + epsilon(t)
b(institute) ~ N(0, 0.0075^2) [static within the series]
epsilon(t) ~ N(0, (max(1e-8, p*(1-p)*DEFF/n) + R) / multiplier)
```

The explicit institute-offset prior prevents an institute's repeated surveys
from falsely eliminating uncertainty about its level. It is a local sensitivity
assumption, not a historically learned institute bias. The posterior includes
the resulting covariance between latent support and offsets. Independent party
marginals are sampled, bounded, and normalized to a vote-share composition; a
multivariate party covariance was not fitted.

When a report separately publishes undecided share but not the number of decided
respondents, the input may provide `percentageSampleSize = actual_n * (1 - undecided)`.
That is an approximate decided count for measurement variance, explicitly labelled
as estimated. It is not a newly reported actual count or the survey's weighted
effective sample size; design effect remains a separate sensitivity assumption.

`Q` and additional residual `R` are estimated on a nonnegative grid by sequential
one-step-ahead Gaussian predictive likelihood plus a disclosed weak low-variance
penalty. The first survey initializes diffuse latent support, is conditioned on
once, and is not scored twice in the likelihood. Fewer than 8 unique institute/day
observations or less than 14 calendar days uses explicit fallback `Q=0.0006^2`
per day, `R=0.003^2`. These are sensitivity settings, not learned forecast skill.
Hyperparameter estimation uncertainty is not integrated out.

Only actual published percentages with a documented compatible valid-vote/decided-voter
denominator enter the fit. When the denominator is inferred from a complete
table's total and separately reported undecided share, that inference must be
retained in the source audit, rather than described as an explicit source label.
Fieldwork must be verified, entirely after 8 September
2026, no later than publication, and both must precede the selected as-of date.
No reconstructed seat-to-share conversion, unknown denominator, unpublished
zero, aggregator forecast, or future row can enter as an observation. Duplicate
poll IDs are collapsed; conflicting duplicates fail. Same-institute/day reports
are averaged once while retaining the largest variance, without increasing n.

Existing historical accuracy weights are already shrunk by the site's limited
historical benchmark. In this mode they are normalized across selected
institutes that have eligible percentage data and multiply user controls once in
the measurement variance. Toggling an institute with no eligible percentage data
therefore cannot rescale the measurement uncertainty of the supported institutes. They
are not applied a second time to filtered outputs or effective contributions.
Turning the flag off uses neutral historical weights. The attribution table
preserves per-party linear coefficients, which can be negative when correcting
an institute offset; aggregate display weights summarize their magnitudes and
are not the computational weights of an additional poll mixture.

Missing parties cause an explicit error unless reviewed data supplies a named
sensitivity prior with source/reason or an actual published interval bound. Such
values are labelled as priors, never observations. General prior mean/SD values
are fractions after conversion from `meanPct`/`sdPct`; a published interval uses
an explicitly stated uniform-within-bound sensitivity assumption.

Posterior simulation must not add the legacy poll-selection mixture, Dirichlet
sampling, seat-rounding jitter, or dailyDrift to this posterior. `Q*forecastDays`
already advances the latent state uncertainty. A separate explicitly labelled
shared bloc-error sensitivity may be applied once by the caller.

The alternative has not been validated as superior to existing methods on
held-out elections. Its crossing-threshold and majority probabilities are
conditional, experimental model outputs, not calibrated election guarantees.
