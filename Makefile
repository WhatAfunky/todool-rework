build:
	@odin build src -out:target/todool -thread-count:12 && cd target && ./todool

release:
	@odin build src -out:target/todool -o:speed -thread-count:12 

debug: 
	@odin build src -out:target/todool -debug -thread-count:12 

run:
	@cd target && ./todool

check:
	@odin check src -thread-count:12

# macOS only: optimized build packaged as target/Todool.app
app: release
	@python3 scripts/bundle_mac.py target/todool
