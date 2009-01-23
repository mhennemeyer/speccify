require File.dirname(__FILE__) + "/test_helper.rb"

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
end


describe "top level description block with one example" do
  
  before do
    @horst = "Horst"
  end
  
  it "example3" do
    @horst.should == "Horst"
  end

  describe "second level description block" do

    before do
      @inge = "Inge"
    end
    
    it "Inge should be here" do
      @inge.should == "Inge"
    end
    
    it "Horst should still be here" do
      @horst.should == "Horst"
    end

  end
end


# class Thing
#   def widgets
#     @widgets ||= []
#   end
# end

describe "Thing" do
  
  before do
    @thing = 1
  end
  describe "initialized in first before" do
    before {}
    it "has 0 widgets" do
      @thing.should == 1
    end
  end
end