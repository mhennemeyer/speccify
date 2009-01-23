Feature: before and after blocks

  As a developer using RSpec
  I want to execute arbitrary code before and after each example
  So that I can control the environment in which it is run
  
    This is supported by the before and after methods 
  
  
  Scenario: define before(:each) block in example group
    Given the following spec:
      """
      require "/Users/macbook/Projekte/midi-spec/lib/midi_spec.rb"
      
      class Thing
        def widgets
          @widgets ||= []
        end
      end
      
      def_matcher :have do |given, matcher, args|
        number = given.send(matcher.fn.name).length
        args[0] == number
      end

      describe "Thing" do
        before do
          @thing = Thing.new
        end

        describe "initialized in first before" do
          it "has 0 widgets" do
            @thing.should have(0).widgets
          end
        
          it "can get accept new widgets" do
            @thing.widgets << Object.new
          end
        
          it "does not share state across examples" do
            @thing.should have(0).widgets
          end
          
          describe "changed in second before" do
            before do
              @thing.widgets << Object.new
            end
            it "has 1 widgets" do
              @thing.should have(1).widgets
            end

            it "can get accept new widgets" do
              @thing.widgets << Object.new
            end

            it "does not share state across examples" do
              @thing.should have(1).widgets
            end
          end
        end
      end
      """
  	When I run it with the ruby interpreter
  	Then the stderr should be blank
    And the stdout should match "6 tests, 4 assertions, 0 failures, 0 errors, 0 skips"
    
  