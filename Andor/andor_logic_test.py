#!/usr/bin/env python3
"""
Comprehensive test code for AndorCameraLogic class.
Tests all functions and acquisition modes with plotting.
"""

import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QEventLoop
if __package__:
    from .andor_logic import AndorCameraLogic
else:
    from andor_logic import AndorCameraLogic


class AndorCameraTest:
    """Test suite for Andor Camera Logic with comprehensive function testing."""

    def __init__(self):
        self.logic = AndorCameraLogic()
        self.test_results = {}
        self.captured_images = []

        # Connect signals to capture results
        self.logic.sig_image_acquired.connect(self.on_image_acquired)
        self.logic.sig_connected.connect(self.on_connection_changed)
        self.logic.sig_is_changing.connect(self.on_status_changed)

    def on_image_acquired(self, image):
        """Store acquired images for analysis."""
        self.captured_images.append(image)
        print(f"📸 Image acquired: shape {image.shape}, dtype {image.dtype}")

    def on_connection_changed(self, status):
        """Handle connection status changes."""
        print(f"🔌 Connection: {status}")

    def on_status_changed(self, status):
        """Handle status messages."""
        print(f"📊 Status: {status}")

    def test_connection(self):
        """Test camera connection and basic info queries."""
        print("\n" + "="*60)
        print("🚀 TESTING CONNECTION AND BASIC INFO")
        print("="*60)

        try:
            # Test connection
            self.logic.connect_camera(camera_index=0)

            # Test query functions (non-scan info)
            device_info = self.logic.query_device_info()
            detector_size = self.logic.query_detector_size()
            acquisition_timings = self.logic.query_acquisition_timings()

            self.test_results['connection'] = True
            self.test_results['device_info'] = device_info
            self.test_results['detector_size'] = detector_size
            self.test_results['acquisition_timings'] = acquisition_timings

            print(f"✅ Device Info: {device_info}")
            print(f"✅ Detector Size: {detector_size}")
            print(f"✅ Acquisition Timings: {acquisition_timings}")

        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            self.test_results['connection'] = False
            raise

    def test_query_functions(self):
        """Test all query_xxx functions (non-scan readable)."""
        print("\n" + "="*60)
        print("📋 TESTING QUERY FUNCTIONS (Non-scan)")
        print("="*60)

        query_functions = [
            ('query_acquisition_mode', 'Acquisition Mode'),
            ('query_exposure_time', 'Exposure Time'),
            ('query_read_mode', 'Read Mode'),
        ]

        for func_name, desc in query_functions:
            try:
                func = getattr(self.logic, func_name)
                result = func()
                self.test_results[func_name] = result
                print(f"✅ {desc}: {result}")
            except Exception as e:
                print(f"❌ {func_name} failed: {e}")
                self.test_results[func_name] = None

    def test_get_functions(self):
        """Test all get_xxx functions (scan readable)."""
        print("\n" + "="*60)
        print("📖 TESTING GET FUNCTIONS (Scan readable)")
        print("="*60)

        # Note: Based on your code, only get_temperature exists as a scan readable function
        get_functions = [
            ('get_temperature', 'Temperature'),
        ]

        for func_name, desc in get_functions:
            try:
                func = getattr(self.logic, func_name)
                result = func()
                self.test_results[func_name] = result
                print(f"✅ {desc}: {result}")
            except Exception as e:
                print(f"❌ {func_name} failed: {e}")
                self.test_results[func_name] = None

    def test_set_functions(self):
        """Test all set_xxx functions (scan settable)."""
        print("\n" + "="*60)
        print("⚙️  TESTING SET FUNCTIONS (Scan settable)")
        print("="*60)

        # Note: Based on your code, only set_temperature exists as a scan settable function
        # Test temperature setting
        try:
            original_temp = self.logic.setpoint_temperature

            # Test setting temperature
            self.logic.setpoint_temperature = -70
            self.logic.set_temperature()

            # Verify it was set
            time.sleep(1)  # Allow time for setting
            current_temp = self.logic.get_temperature()

            self.test_results['set_temperature'] = current_temp
            print(f"✅ Temperature set to: {self.logic.setpoint_temperature}°C")
            print(f"✅ Current temperature: {current_temp}°C")

            # Restore original
            self.logic.setpoint_temperature = original_temp

        except Exception as e:
            print(f"❌ set_temperature failed: {e}")
            self.test_results['set_temperature'] = None

    def test_setup_functions(self):
        """Test all setup_xxx functions (non-scan configuration)."""
        print("\n" + "="*60)
        print("🔧 TESTING SETUP FUNCTIONS (Non-scan configuration)")
        print("="*60)

        setup_tests = [
            {
                'name': 'setup_exposure_time',
                'setpoint': 'setpoint_exposure_time',
                'value': 0.05,
                'desc': 'Exposure Time Setup'
            },
            {
                'name': 'setup_read_mode',
                'setpoint': 'setpoint_read_mode',
                'value': 'image',
                'desc': 'Read Mode Setup'
            },
            {
                'name': 'setup_acquisition_mode',
                'setpoint': 'setpoint_acquisition_mode',
                'value': 'single',
                'desc': 'Acquisition Mode Setup'
            }
        ]

        for test in setup_tests:
            try:
                # Set the setpoint
                setattr(self.logic, test['setpoint'], test['value'])

                # Call the setup function
                func = getattr(self.logic, test['name'])
                func()

                self.test_results[test['name']] = test['value']
                print(f"✅ {test['desc']}: {test['value']}")

            except Exception as e:
                print(f"❌ {test['name']} failed: {e}")
                self.test_results[test['name']] = None

    def test_single_acquisition(self):
        """Test single image acquisition."""
        print("\n" + "="*60)
        print("📷 TESTING SINGLE ACQUISITION")
        print("="*60)

        try:
            # Setup single mode
            self.logic.setpoint_acquisition_mode = "single"
            self.logic.setpoint_exposure_time = 0.1
            self.logic.setup_acquisition_mode()
            self.logic.setup_exposure_time()

            # Clear previous images
            self.captured_images.clear()

            # Snap image
            image = self.logic.snap_image()

            if image is not None:
                self.test_results['single_acquisition'] = {
                    'success': True,
                    'shape': image.shape,
                    'dtype': str(image.dtype),
                    'mean': float(np.mean(image)),
                    'std': float(np.std(image))
                }
                print(f"✅ Single image acquired: shape {image.shape}")
                print(f"✅ Image stats: mean={np.mean(image):.2f}, std={np.std(image):.2f}")
            else:
                raise ValueError("No image returned")

        except Exception as e:
            print(f"❌ Single acquisition failed: {e}")
            self.test_results['single_acquisition'] = {'success': False, 'error': str(e)}

    def test_continuous_acquisition(self):
        """Test continuous acquisition mode."""
        print("\n" + "="*60)
        print("🎬 TESTING CONTINUOUS ACQUISITION")
        print("="*60)

        try:
            # Setup continuous mode
            self.logic.setpoint_acquisition_mode = "continuous"
            self.logic.setpoint_cont_cycle_time = 0.05
            self.logic.setpoint_exposure_time = 0.02

            self.logic.setup_continuous_mode()
            self.logic.setup_acquisition_mode()
            self.logic.setup_exposure_time()

            # Clear previous images
            self.captured_images.clear()

            # Start continuous acquisition
            self.logic.start_acquisition()

            # Collect frames
            images = []
            num_frames = 5
            for i in range(num_frames):
                self.logic.wait_for_frame()
                image = self.logic.read_oldest_image()
                images.append(image)
                print(f"📸 Frame {i+1}/{num_frames} captured: shape {image.shape}")

            self.logic.stop_acquisition()

            if len(images) > 0:
                self.test_results['continuous_acquisition'] = {
                    'success': True,
                    'num_frames': len(images),
                    'frame_shapes': [img.shape for img in images],
                    'mean_values': [float(np.mean(img)) for img in images]
                }
                print(f"✅ Continuous acquisition: {len(images)} frames captured")
            else:
                raise ValueError("No frames captured")

        except Exception as e:
            print(f"❌ Continuous acquisition failed: {e}")
            self.test_results['continuous_acquisition'] = {'success': False, 'error': str(e)}

    def test_accumulation_acquisition(self):
        """Test accumulation acquisition mode."""
        print("\n" + "="*60)
        print("📚 TESTING ACCUMULATION ACQUISITION")
        print("="*60)

        try:
            # Setup accumulation mode
            self.logic.setpoint_acquisition_mode = "accumulate"
            self.logic.setpoint_accum_num_frames = 5
            self.logic.setpoint_accum_cycle_time = 0.11824
            self.logic.setpoint_exposure_time = 0.02

            self.logic.setup_acquisition_mode()
            self.logic.setup_accumulation_mode()
            self.logic.setup_exposure_time()

            # Clear previous images
            self.captured_images.clear()

            # Start acquisition and get accumulated image
            self.logic.start_acquisition()
            # image = self.logic.snap_image()
            self.logic.wait_for_frame()
            image = self.logic.read_newest_image()
            self.logic.stop_acquisition()

            if image is not None:
                self.test_results['accumulation_acquisition'] = {
                    'success': True,
                    'shape': image.shape,
                    'num_accumulations': self.logic.setpoint_accum_num_frames,
                    'mean': float(np.mean(image)),
                    'std': float(np.std(image))
                }
                print(f"✅ Accumulation acquisition: {self.logic.setpoint_accum_num_frames} frames accumulated")
                print(f"✅ Result shape: {image.shape}, mean: {np.mean(image):.2f}")
            else:
                raise ValueError("No accumulated image returned")

        except Exception as e:
            print(f"❌ Accumulation acquisition failed: {e}")
            self.test_results['accumulation_acquisition'] = {'success': False, 'error': str(e)}

    def test_kinetic_acquisition(self):
        """Test kinetic acquisition mode."""
        print("\n" + "="*60)
        print("⚡ TESTING KINETIC ACQUISITION")
        print("="*60)

        try:
            # Setup kinetic mode
            self.logic.setpoint_acquisition_mode = "kinetic"
            self.logic.setpoint_kinetic_num_cycle = 3
            self.logic.setpoint_kinetic_cycle_time = 0.1
            self.logic.setpoint_kinetic_num_acc = 2
            self.logic.setpoint_exposure_time = 0.02

            self.logic.setup_kinetic_mode()
            self.logic.setup_acquisition_mode()
            self.logic.setup_exposure_time()

            # Clear previous images
            self.captured_images.clear()

            # Start kinetic acquisition
            self.logic.start_acquisition()

            # Collect kinetic series
            images = []
            for i in range(self.logic.setpoint_kinetic_num_cycle):
                self.logic.wait_for_frame()
                image = self.logic.read_oldest_image()
                images.append(image)
                print(f"⚡ Kinetic cycle {i+1}/{self.logic.setpoint_kinetic_num_cycle}")

            self.logic.stop_acquisition()

            if len(images) > 0:
                self.test_results['kinetic_acquisition'] = {
                    'success': True,
                    'num_cycles': len(images),
                    'num_acc_per_cycle': self.logic.setpoint_kinetic_num_acc,
                    'cycle_shapes': [img.shape for img in images],
                    'cycle_means': [float(np.mean(img)) for img in images]
                }
                print(f"✅ Kinetic acquisition: {len(images)} cycles completed")
            else:
                raise ValueError("No kinetic images captured")

        except Exception as e:
            print(f"❌ Kinetic acquisition failed: {e}")
            self.test_results['kinetic_acquisition'] = {'success': False, 'error': str(e)}

    def test_buffer_operations(self):
        """Test buffer operations and frame management."""
        print("\n" + "="*60)
        print("🗃️  TESTING BUFFER OPERATIONS")
        print("="*60)

        try:
            # Setup for buffer testing
            self.logic.setpoint_acquisition_mode = "continuous"
            self.logic.setup_continuous_mode()
            self.logic.setup_acquisition_mode()

            # Test buffer clear
            self.logic.clear_acquisition()
            print("✅ Buffer cleared successfully")

            # Test frame status (if available)
            try:
                status = self.logic.hardware.get_frames_status()
                print(f"✅ Frame status: {status}")
                self.test_results['buffer_status'] = status
            except:
                print("ℹ️  Frame status not available")
                self.test_results['buffer_status'] = None

            self.test_results['buffer_operations'] = {'success': True}

        except Exception as e:
            print(f"❌ Buffer operations failed: {e}")
            self.test_results['buffer_operations'] = {'success': False, 'error': str(e)}

    def plot_results(self):
        """Plot acquired images and test results."""
        print("\n" + "="*60)
        print("📊 PLOTTING RESULTS")
        print("="*60)

        if not self.captured_images:
            print("⚠️  No images to plot")
            return

        # Create figure with subplots
        num_images = min(len(self.captured_images), 6)  # Limit to 6 images
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Andor Camera Test Results', fontsize=16, fontweight='bold')

        axes = axes.flatten()

        for i in range(num_images):
            image = self.captured_images[i]

            # Handle different image dimensions
            if len(image.shape) == 2:
                # 2D image
                im = axes[i].imshow(image, cmap='gray', aspect='auto')
                plt.colorbar(im, ax=axes[i])
            elif len(image.shape) == 1:
                # 1D spectrum
                axes[i].plot(image)
                axes[i].set_ylabel('Intensity')
                axes[i].set_xlabel('Pixel')
            else:
                # Multi-dimensional - show a slice
                axes[i].imshow(image[:, :, 0] if image.shape[2] > 0 else image.reshape(-1, 1),
                              cmap='gray', aspect='auto')

            # Add statistics
            mean_val = np.mean(image)
            std_val = np.std(image)
            axes[i].set_title(f'Image {i+1}\nShape: {image.shape}\n'
                             f'Mean: {mean_val:.1f}, Std: {std_val:.1f}')

        # Hide unused subplots
        for i in range(num_images, len(axes)):
            axes[i].axis('off')

        plt.tight_layout()
        plt.show()

        # Plot test results summary
        self.plot_test_summary()

    def plot_test_summary(self):
        """Plot summary of test results."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Test success rates
        test_categories = ['Connection', 'Query Functions', 'Setup Functions',
                          'Acquisitions', 'Buffer Operations']
        success_counts = []

        # Count successes in each category
        connection_success = 1 if self.test_results.get('connection', False) else 0
        success_counts.append(connection_success)

        query_success = sum(1 for k, v in self.test_results.items()
                           if k.startswith('query_') and v is not None)
        success_counts.append(query_success)

        setup_success = sum(1 for k, v in self.test_results.items()
                           if k.startswith('setup_') and v is not None)
        success_counts.append(setup_success)

        acq_success = sum(1 for k, v in self.test_results.items()
                         if 'acquisition' in k and isinstance(v, dict) and v.get('success', False))
        success_counts.append(acq_success)

        buffer_success = 1 if self.test_results.get('buffer_operations', {}).get('success', False) else 0
        success_counts.append(buffer_success)

        # Bar chart of successes
        colors = ['green' if x > 0 else 'red' for x in success_counts]
        bars = ax1.bar(test_categories, success_counts, color=colors, alpha=0.7)
        ax1.set_title('Test Results Summary')
        ax1.set_ylabel('Number of Successful Tests')
        ax1.set_ylim(0, max(success_counts) + 1 if success_counts else 1)

        # Add value labels on bars
        for bar, count in zip(bars, success_counts):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                    f'{count}', ha='center', va='bottom')

        # Image statistics if available
        if self.captured_images:
            image_means = [np.mean(img) for img in self.captured_images]
            image_stds = [np.std(img) for img in self.captured_images]

            x = range(len(image_means))
            ax2.errorbar(x, image_means, yerr=image_stds, marker='o', capsize=5)
            ax2.set_title('Image Statistics')
            ax2.set_xlabel('Image Index')
            ax2.set_ylabel('Mean Intensity ± Std')
            ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No images captured',
                    transform=ax2.transAxes, ha='center', va='center')
            ax2.set_title('Image Statistics - No Data')

        plt.tight_layout()
        plt.show()

    def print_test_report(self):
        """Print comprehensive test report."""
        print("\n" + "="*60)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("="*60)

        total_tests = len(self.test_results)
        successful_tests = sum(1 for v in self.test_results.values()
                              if (isinstance(v, dict) and v.get('success', False)) or
                                 (v is not None and not isinstance(v, dict)))

        print(f"📊 Overall Success Rate: {successful_tests}/{total_tests} "
              f"({100*successful_tests/total_tests if total_tests > 0 else 0:.1f}%)")
        print()

        for test_name, result in self.test_results.items():
            status = "✅" if ((isinstance(result, dict) and result.get('success', False)) or
                             (result is not None and not isinstance(result, dict))) else "❌"
            print(f"{status} {test_name}: {result}")

        if self.captured_images:
            print(f"\n📷 Total Images Captured: {len(self.captured_images)}")
            for i, img in enumerate(self.captured_images[:5]):  # Show first 5
                print(f"   Image {i+1}: shape={img.shape}, mean={np.mean(img):.2f}")

    def run_all_tests(self):
        """Run the complete test suite."""
        print("🧪 Starting Andor Camera Logic Test Suite")
        print("="*60)

        try:
            # Basic connection and info tests
            self.test_connection()

            # Function tests
            self.test_query_functions()
            self.test_get_functions()
            self.test_set_functions()
            self.test_setup_functions()

            # Acquisition mode tests
            self.test_single_acquisition()
            self.test_continuous_acquisition()
            # self.test_accumulation_acquisition()
            # self.test_kinetic_acquisition()

            # Buffer operation tests
            self.test_buffer_operations()

            # Results analysis
            self.print_test_report()
            self.plot_results()

        except Exception as e:
            print(f"\n💥 Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Clean up
            try:
                if self.logic.acquiring:
                    self.logic.stop_acquisition()
                self.logic.disconnect()
            except:
                pass


def main():
    """Main test function."""
    app = QApplication(sys.argv)

    # Create and run test suite
    test = AndorCameraTest()

    try:
        test.run_all_tests()

        # Keep application running briefly to show plots
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(1000)  # Quit after 1 second to show plots

        app.exec()

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Test suite completed")


if __name__ == "__main__":
    main()
