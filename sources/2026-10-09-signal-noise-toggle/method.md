# Independent signal/noise feature: model contract

This is our experimental local adaptation inspired by Ariel Danieli / To120. It is not a copy of To120's code, calibration, compiled inputs or forecasts. The source credit remains in the engine and the website. No improvement in out-of-sample election prediction or probability calibration is claimed.

`signalNoiseEnabled` controls support estimation independently of the existing `weightMode`. With the feature off, the existing combination and simulation path is preserved. With it on, the selected policy supplies relative measurement reliability to the local-level filter. All subsequent turnout, party motivation, bloc classification, threshold, surplus-agreement and seat-allocation calculations share the same simulation result.

## Reliability policy

1. Compute the chosen existing policy on the active latest poll from each institute. Its manual multipliers are already included. Arithmetic ensembles and nonlinear robust combinations remain operators on the same policy vectors; the filtered posterior is never added as another ensemble member or independent poll.
2. Admit only the separate source-reviewed percentage observations whose publication and verified fieldwork fall within the strict post-closure window. A zero institute weight removes its history. An institute with no compatible percentage report contributes no observations or precision.
3. Normalize the positive policy masses to a mean of one across institutes that have compatible percentage observations. For observation `i` from institute `s`, use `V_i = (known_sampling_variance_i + fitted_R) / reliability_s` inside the Kalman fit. Historical accuracy and manual multipliers are not applied again after filtering.
4. Learn latent daily movement `Q` and additional measurement noise `R` by regularized one-step predictive likelihood, with the existing disclosed fallback for short series and a prior variance for static institute offsets. No second per-observation recency decay is applied. A requested forward horizon adds `Q × days` to posterior variance once.
5. Sample the existing approximation of independent party posterior marginals, normalize to total support, and apply the separately disclosed shared-bloc sensitivity once. No legacy poll-mixture draw, seat-rounding jitter or additional legacy daily drift is added to this posterior.

These confidence multipliers are an adaptation of the selected policy, not promises that a party's final filtered estimate has the same fixed weights as a latest-poll average. Known sample size already affects sampling variance; a policy such as Rosner's proxy can additionally use sample size, freshness and outlier rules to set relative institute trust. Reconstructed current mandate vectors can help identify policy outliers, but they never enter the time series as source vote percentages.

If an institute targeted by a policy (for example a 50% scenario) lacks compatible percentage observations, the available source cohort is renormalized and that target share need not hold. Metadata names these coverage gaps. Static published poll tables and the existing published-mandate trend/significance analyses remain evidence about published results; enabling a forecast filter does not rewrite them.

## Metadata and safeguards

`result.signalNoise.weightingPolicy` records the selected mode, latest policy weights, mean-one reliability multipliers, aggregation, zero-weight exclusions and unavailable institutes. `combined.policyWeights` carries the policy vector for static transparency; `combined.weights` remains the descriptive absolute filter-contribution summary and must not be labeled as fixed policy weights.

A policy with duplicate or mismatched active poll IDs is rejected. Snapshot policy publications later than the requested forecast date are rejected, rather than leaking future outlier or recency information into a retrospective forecast. Retrospective forecasting would require a policy roster derived at that earlier date.

The numerical limitations remain: short series may not separately identify `Q` and `R`; institute-offset uncertainty is conditional on its stated prior; cross-party covariance is approximated rather than jointly fitted; the posterior crossing-threshold and majority probabilities have not been calibrated on elections held out of development. A fitted `Q = 0` is not a significance test or proof of no change.

The old direct `createSignalNoiseCombination` API without a policy retains its historical-quality/manual semantics for compatibility. The independent feature passes an explicit policy and ignores that legacy flag when deciding reliability, preventing double application of historical accuracy.
