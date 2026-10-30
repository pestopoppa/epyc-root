import control_driver
try:control_driver.main()
except FileNotFoundError as e:
 assert e.filename.endswith('ROOT-REVIEW.json')
 print('review gate refuses before model launch')
else:raise AssertionError('review missing accepted')
