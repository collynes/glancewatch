class Glancewatch < Formula
  include Language::Python::Virtualenv

  desc "Lightweight monitoring adapter for Glances + Uptime Kuma"
  homepage "https://github.com/collynes/glancewatch"
  url "https://files.pythonhosted.org/packages/source/g/glancewatch/glancewatch-1.2.5.tar.gz"
  sha256 "TBD_AFTER_PYPI_UPLOAD"
  license "MIT"

  depends_on "python@3.12"

  def install
    # Install glancewatch and all dependencies via pip (uses pre-built wheels)
    system "python3.12", "-m", "venv", libexec
    system libexec/"bin/pip", "install", "--upgrade", "pip"
    system libexec/"bin/pip", "install", "glancewatch==1.2.5"
    
    # Create wrapper script
    bin.install_symlink libexec/"bin/glancewatch"
  end

  service do
    run opt_bin/"glancewatch"
    working_dir var/"glancewatch"
    keep_alive true
    log_path var/"log/glancewatch.log"
    error_log_path var/"log/glancewatch.error.log"
  end

  test do
    system bin/"glancewatch", "--version"
  end
end
