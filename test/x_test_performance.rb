require File.dirname(__FILE__) + "/test_helper.rb"

class Thing
  def widgets
    @widgets ||= []
  end
end

def_matcher :be_in_range do |given, matcher, args|
  range = args[1] ? (args[0]..args[1]) : args[0]
  matcher.positive_msg = "expected #{given} to be in range (#{range})"
  matcher.negative_msg = "expected #{given} not to be in range (#{range})"
  range.include?(given)
end

def_matcher :have do |given, matcher, args|
  number = args[0]
  actual = given.send(matcher.msgs[0].name).length
  matcher.positive_msg = "Expected #{given} to have #{actual}, but found #{number} "
  actual == number
end

100.times do |i|
  
  describe "Matcher: be_in_range#{i}" do
    describe "With lower and upper bound seperately#{i}" do
      describe "Given value of 1 #{i}" do

        before do
          @value = 1
        end

        it "should be in range (0,1), #{i}" do
          @value.should be_in_range(0,1)
        end

        it "should be in range (1,1), #{i}" do
          @value.should be_in_range(1,1)
        end

        it "should be in range (1,2), #{i}" do
          @value.should be_in_range(1,2)
        end

        it "should not be in range (0,0), #{i}" do
          @value.should_not be_in_range(0,0)
        end

        it "should not be in range (2,2), #{i}" do
          @value.should_not be_in_range(2,2)
        end
      end

      describe "With range (), #{i}" do
        describe "Given value of 1" do

          before do
            @value = 1
          end

          it "should be in range (0,1), #{i}" do
            @value.should be_in_range(0..1)
          end

          it "should be in range (1,1), #{i}" do
            @value.should be_in_range(1..1)
          end

          it "should be in range (1,2), #{i}" do
            @value.should be_in_range(1..2)
          end

          it "should not be in range (0,0), #{i}" do
            @value.should_not be_in_range(0..0)
          end

          it "should not be in range (2,2), #{i}" do
            @value.should_not be_in_range(2..2)
          end
        end
      end
    end
  end


  describe "top level description block with one example, #{i}" do

    before do
      @horst = "Horst"
    end

    it "example3, #{i}" do
      @horst.should == "Horst"
    end

    describe "second level description block, #{i}" do

      before do
        @inge = "Inge"
      end

      it "Inge should be here, #{i}" do
        @inge.should == "Inge"
      end

      it "Horst should still be here, #{i}" do
        @horst.should == "Horst"
      end

    end
  end

  describe "Thing, #{i}" do

    before do
      @thing = Thing.new
    end
    describe "initialized in first before,#{i}" do
      before {}
      it "has 0 widgets, #{i}" do
        @thing.should have(0).widgets
      end
    end
  end
end