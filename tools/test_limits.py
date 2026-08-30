"""Simulates the notebook's stop/shrink control flow with synthetic epoch times.

Mirrors the two decision branches in the training cell (it does not import them --
they live inside the .ipynb). If you edit those branches, edit these too.
"""

EPOCHS, TIME_BUDGET_HOURS, MIN_TRAIN_IMAGES, AUTO_SHRINK = 15, 3.0, 200, True
BUDGET = TIME_BUDGET_HOURS * 3600


def run(epoch_seconds_for, n_train, auto_shrink=AUTO_SHRINK, epochs=EPOCHS):
    """Returns (epochs_run, total_seconds, final_train_size, stopped_early)."""
    budget_s = TIME_BUDGET_HOURS * 3600
    elapsed = 0.0
    stopped_early = False
    for epoch in range(1, epochs + 1):
        epoch_s = epoch_seconds_for(n_train)
        elapsed += epoch_s

        # --- branch 1: shrink once after epoch 1 (mirrors notebook) ---
        if auto_shrink and epoch == 1 and n_train > MIN_TRAIN_IMAGES:
            projected = epoch_s * epochs
            if projected > budget_s:
                keep = max(MIN_TRAIN_IMAGES, int(n_train * (budget_s * 0.9) / projected))
                if keep < n_train:
                    n_train = keep

        # --- branch 2: stop before an epoch that would overrun (mirrors notebook) ---
        if epoch < epochs and elapsed + epoch_s > budget_s:
            stopped_early = True
            return epoch, elapsed, n_train, stopped_early
    return epochs, elapsed, n_train, stopped_early


# epoch time scales linearly with training-set size
def linear(sec_per_image):
    return lambda n: n * sec_per_image


FULL = 6455  # Deep-SAR train split

# 1. Fast enough: all 15 epochs, no shrink, inside budget.
ep, t, n, early = run(linear(0.05), FULL)          # ~5.4 min/epoch
assert (ep, n, early) == (15, FULL, False), (ep, n, early)
assert t < BUDGET, t
print(f"1. fast      -> {ep} epochs, {t/3600:.2f}h, {n} imgs, no shrink          OK")

# 2. Slow: shrinks once, then still completes all 15 inside budget.
ep, t, n, early = run(linear(0.14), FULL)          # ~15 min/epoch, projects to 3.8h
assert ep == 15 and not early, (ep, early)
assert MIN_TRAIN_IMAGES <= n < FULL, n
assert t < BUDGET, f"shrink failed to bring run inside budget: {t/3600:.2f}h"
print(f"2. slow      -> {ep} epochs, {t/3600:.2f}h, shrank {FULL} -> {n}        OK")

# 3. Very slow: shrinks hard, still lands inside budget.
ep, t, n, early = run(linear(0.62), FULL)          # ~67 min/epoch
assert n >= MIN_TRAIN_IMAGES, n
assert t < BUDGET, f"{t/3600:.2f}h"
print(f"3. very slow -> {ep} epochs, {t/3600:.2f}h, shrank {FULL} -> {n}        OK")

# 4. Shrink disabled: keeps every image, stops early on the time budget instead.
ep, t, n, early = run(linear(0.14), FULL, auto_shrink=False)
assert n == FULL and early and ep < 15, (n, early, ep)
assert t < BUDGET, f"overran budget: {t/3600:.2f}h"
print(f"4. no-shrink -> stopped at epoch {ep}, {t/3600:.2f}h, {n} imgs kept     OK")

# 5. Pathological: one epoch alone exceeds the budget. Runs once, then stops.
#    Cannot be prevented -- the cost is only knowable after running it.
ep, t, n, early = run(lambda n: 4 * 3600, FULL)
assert (ep, early) == (1, True), (ep, early)
assert t > BUDGET, t
print(f"5. 4h epoch  -> stopped at epoch {ep}, {t/3600:.2f}h (overrun unavoidable) OK")

# 6. Small dataset already at the floor: never shrinks below MIN_TRAIN_IMAGES.
ep, t, n, early = run(linear(2.0), MIN_TRAIN_IMAGES)
assert n == MIN_TRAIN_IMAGES, n
print(f"6. at floor  -> {n} imgs, not shrunk below MIN_TRAIN_IMAGES           OK")

# 7. Budget is never overrun except in the pathological single-epoch case.
for spi in (0.02, 0.05, 0.1, 0.14, 0.3, 0.62, 1.0):
    ep, t, n, early = run(linear(spi), FULL)
    if spi * FULL < BUDGET:
        assert t < BUDGET, f"sec/img={spi}: overran at {t/3600:.2f}h"
print("7. sweep     -> no overrun across 7 speed regimes                     OK")

print()
print("ALL LIMIT CHECKS PASSED")
