import unittest
from tinygrad.jit import TinyJit
from tinygrad.helpers import getenv
from tinygrad.shape.symbolic import Variable
from tinygrad.tensor import Tensor, Device
import numpy as np

@unittest.skipIf(getenv("ARM64") or getenv("PTX"), "ARM64 and PTX are not supported")
@unittest.skipUnless(Device.DEFAULT in ["GPU", "METAL", "CLANG", "CUDA"], f"{Device.DEFAULT} is not supported")
class TestSymbolicJit(unittest.TestCase):
  def test_plus1(self):
    def f(a): return (a+1).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      a = Tensor.rand(3, i)
      symbolic = jf(a.reshape(3, vi)).reshape(3, i).cpu().numpy()
      expected = f(a).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_add(self):
    def f(a, b): return (a+b).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      a = Tensor.rand(3, i)
      b = Tensor.rand(3, i)
      symbolic = jf(a.reshape(3, vi), b.reshape(3, vi)).reshape(3, i).cpu().numpy()
      expected = f(a, b).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_matmul(self):
    def f(a, b): return (a@b).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      a = Tensor.rand(3, i)
      b = Tensor.rand(i, 5)
      symbolic = jf(a.reshape(3, vi), b.reshape(vi, 5)).cpu().numpy()
      expected = f(a, b).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_mixed_with_no_symbol_kernel(self):
    def f(a, b):
      s = (a@b).realize()
      s = (s+s).realize() # this one does not have symbols in input
      return s
    jf = TinyJit(f)
    for i in range(1, 5):
      vi = Variable("i", 1, 10)
      a = Tensor.rand(3, i)
      b = Tensor.rand(i, 5)
      symbolic = jf(a.reshape(3, vi), b.reshape(vi, 5)).cpu().numpy()
      expected = f(a, b).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 2

  @unittest.skipIf(Device.DEFAULT == "CLANG", "broken on CLANG CI")
  def test_attention(self):
    def f(q, k, v): return Tensor.scaled_dot_product_attention(q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      q = Tensor.rand(2, 1, 4, 8)
      k = Tensor.rand(2, i, 4, 8)
      v = Tensor.rand(2, i, 4, 8)
      symbolic = jf(q, k.reshape(2, vi, 4, 8), v.reshape(2, vi, 4, 8)).reshape(2, 4, 1, 8).cpu().numpy()
      expected = f(q, k, v).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 6

  def test_cat_dim0(self):
    def f(a, b): return a.cat(b, dim=0).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      a = Tensor.rand(i, 3)
      b = Tensor.rand(2, 3)
      symbolic = jf(a.reshape(vi, 3), b).reshape(i+2, 3).cpu().numpy()
      expected = f(a, b).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_cat_dim1(self):
    def f(a, b): return a.cat(b, dim=1).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      a = Tensor.rand(3, i)
      b = Tensor.rand(3, 2)
      symbolic = jf(a.reshape(3, vi), b).reshape(3, i+2).cpu().numpy()
      expected = f(a, b).cpu().numpy()
      np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_cat_dim0_two_vars(self):
    def f(a, b): return a.cat(b, dim=0).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    vj = Variable("j", 1, 10)
    for i in range(1, 5):
      for j in range(1, 5):
        a = Tensor.rand(i, 3)
        b = Tensor.rand(j, 3)
        symbolic = jf(a.reshape(vi, 3), b.reshape(vj, 3)).reshape(i+j, 3).cpu().numpy()
        expected = f(a, b).cpu().numpy()
        np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_cat_dim1_two_vars(self):
    def f(a, b): return a.cat(b, dim=1).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    vj = Variable("j", 1, 10)
    for i in range(1, 5):
      for j in range(1, 5):
        a = Tensor.rand(3, i)
        b = Tensor.rand(3, j)
        symbolic = jf(a.reshape(3, vi), b.reshape(3, vj)).reshape(3, i+j).cpu().numpy()
        expected = f(a, b).cpu().numpy()
        np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_two_vars_plus1(self):
    def f(a, b): return (a@b+1).realize()
    jf = TinyJit(f)
    vi = Variable("i", 1, 10)
    vj = Variable("j", 1, 10)
    for i in range(1, 5):
      for j in range(1, 5):
        a = Tensor.rand(i, 3)
        b = Tensor.rand(3, j)
        symbolic = jf(a.reshape(vi, 3), b.reshape(3, vj)).reshape(i, j).cpu().numpy()
        expected = f(a, b).cpu().numpy()
        np.testing.assert_allclose(symbolic, expected, atol=1e-6, rtol=1e-6)
    assert len(jf.jit_cache) == 1

  def test_jit_symbolic_shape_mismatch(self):
    @TinyJit
    def add(a, b): return (a+b).realize()
    vi = Variable("i", 1, 10)
    for i in range(1, 5):
      a = Tensor.rand(3, i).reshape(3, vi)
      b = Tensor.rand(3, i).reshape(3, vi)
      c = add(a, b)
    a = Tensor.rand(3, 7).reshape(3, vi)
    bad = Tensor.rand(4, 7).reshape(4, vi)
    with self.assertRaises(AssertionError):
      add(a, bad)