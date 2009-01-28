require File.dirname(__FILE__) + "/../test_helper.rb"

def_matcher :be_in_range do |given, matcher, args|
  range = args[1] ? (args[0]..args[1]) : args[0]
  matcher.positive_msg = "expected #{given} to be in range (#{range})"
  matcher.negative_msg = "expected #{given} not to be in range (#{range})"
  range.include?(given)
end

describe "Matcher: be_in_range" do
  describe "With lower and upper bound seperately" do
    describe "Given value of 1" do
      
      before do
        @value = 1
      end
      
      it "should be in range (0,1)" do
        @value.should be_in_range(0,1)
      end
      
      it "should be in range (1,1)" do
        @value.should be_in_range(1,1)
      end
      
      it "should be in range (1,2)" do
        @value.should be_in_range(1,2)
      end
      
      it "should not be in range (0,0)" do
        @value.should_not be_in_range(0,0)
      end
      
      it "should not be in range (2,2)" do
        @value.should_not be_in_range(2,2)
      end
    end
    
    describe "With range ()" do
      describe "Given value of 1" do

        before do
          @value = 1
        end

        it "should be in range (0,1)" do
          @value.should be_in_range(0..1)
        end

        it "should be in range (1,1)" do
          @value.should be_in_range(1..1)
        end

        it "should be in range (1,2)" do
          @value.should be_in_range(1..2)
        end

        it "should not be in range (0,0)" do
          @value.should_not be_in_range(0..0)
        end

        it "should not be in range (2,2)" do
          @value.should_not be_in_range(2..2)
        end
      end
    end
  end
  describe "Given 'a'" do
    it "should be in range (a,c)" do
      "a".should be_in_range("a","c")
    end
    
    it "should be in range (a..z)" do
      "a".should be_in_range("a".."z")
    end
  end
end

