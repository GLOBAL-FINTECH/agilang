from __future__ import annotations

from agilang.cnn_optimizers import AdamKernelState, adam_update_kernel, maxpool2d_backward, maxpool2d_forward_with_mask


def test_maxpool_forward_records_mask_and_backward_routes_gradient() -> None:
    image = [
        [1, 5],
        [2, 4],
    ]
    result = maxpool2d_forward_with_mask(image, pool_size=2)
    assert result["output"] == [[5.0]]
    assert result["mask"] == [[(0, 1)]]
    grad = maxpool2d_backward([[3.0]], result["mask"], result["input_shape"])
    assert grad == [[0.0, 3.0], [0.0, 0.0]]


def test_adam_update_kernel_changes_weights_and_tracks_state() -> None:
    kernel = [[0.0, 0.0], [0.0, 0.0]]
    grad = [[-1.0, -2.0], [-3.0, -4.0]]
    state = AdamKernelState()
    first = adam_update_kernel(kernel, grad, bias=0.0, grad_bias=-1.0, state=state, learning_rate=0.01)
    assert first["state"].t == 1
    assert first["kernel"][0][0] > 0.0
    second = adam_update_kernel(first["kernel"], grad, bias=first["bias"], grad_bias=-1.0, state=first["state"], learning_rate=0.01)
    assert second["state"].t == 2
    assert second["kernel"][0][0] > first["kernel"][0][0]
